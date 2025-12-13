"""Network Streaming Module

Handles live data streaming from telescope antennas via network protocols.
Supports TCP, UDP, and SPEAD (common in radio astronomy).

This module is for PRODUCTION use only - handles real telescope data streams.
"""
from __future__ import annotations

import socket
import struct
import numpy as np
from typing import Iterator, Optional
from dataclasses import dataclass
import time
import logging

logger = logging.getLogger(__name__)


@dataclass
class StreamConfig:
    """Configuration for network streaming."""
    protocol: str  # 'tcp', 'udp', 'spead'
    host: str
    port: int
    buffer_size: int = 10485760  # 10 MB
    timeout: float = 5.0  # seconds
    expected_sample_rate: float = 1024.0  # Hz
    expected_n_ants: int = 4


class NetworkStreamSource:
    """Base class for network streaming data sources."""
    
    def __init__(self, config: StreamConfig):
        """Initialize network stream source.
        
        Parameters
        ----------
        config : StreamConfig
            Streaming configuration
        """
        self.config = config
        self.socket: Optional[socket.socket] = None
        self.connected = False
        self.packets_received = 0
        self.bytes_received = 0
        self.start_time: Optional[float] = None
        
        logger.info(f"Initializing {config.protocol.upper()} stream source")
        logger.info(f"  Address: {config.host}:{config.port}")
        logger.info(f"  Buffer: {config.buffer_size / 1024 / 1024:.1f} MB")
    
    def connect(self):
        """Establish connection to data source."""
        raise NotImplementedError("Subclass must implement connect()")
    
    def disconnect(self):
        """Close connection to data source."""
        if self.socket:
            self.socket.close()
            self.socket = None
        self.connected = False
        logger.info("Disconnected from stream source")
    
    def receive_chunk(self, chunk_size: int) -> np.ndarray:
        """Receive a chunk of data from the stream.
        
        Parameters
        ----------
        chunk_size : int
            Number of samples to receive
            
        Returns
        -------
        data : ndarray
            Complex voltage samples, shape (n_ants, chunk_size)
        """
        raise NotImplementedError("Subclass must implement receive_chunk()")
    
    def get_statistics(self) -> dict:
        """Get streaming statistics.
        
        Returns
        -------
        stats : dict
            Streaming statistics (packets, bytes, rate, etc.)
        """
        elapsed = time.time() - self.start_time if self.start_time else 0
        return {
            'packets_received': self.packets_received,
            'bytes_received': self.bytes_received,
            'elapsed_time': elapsed,
            'packet_rate': self.packets_received / elapsed if elapsed > 0 else 0,
            'data_rate_mbps': (self.bytes_received * 8 / 1e6) / elapsed if elapsed > 0 else 0,
            'connected': self.connected
        }


class TCPStreamSource(NetworkStreamSource):
    """TCP network streaming source for telescope data."""
    
    def connect(self):
        """Establish TCP connection."""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(self.config.timeout)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, self.config.buffer_size)
            
            logger.info(f"Connecting to {self.config.host}:{self.config.port}...")
            self.socket.connect((self.config.host, self.config.port))
            self.connected = True
            self.start_time = time.time()
            logger.info("✓ TCP connection established")
            
        except socket.error as e:
            logger.error(f"Failed to connect: {e}")
            raise ConnectionError(f"Cannot connect to {self.config.host}:{self.config.port}") from e
    
    def receive_chunk(self, chunk_size: int) -> np.ndarray:
        """Receive data chunk via TCP.
        
        Expected data format: interleaved complex float32 samples
        [ant0_real, ant0_imag, ant1_real, ant1_imag, ...]
        """
        if not self.connected:
            raise ConnectionError("Not connected to stream source")
        
        # Calculate bytes to receive
        # complex64 = 2 floats per sample, 4 bytes per float
        n_ants = self.config.expected_n_ants
        bytes_needed = chunk_size * n_ants * 8  # 8 bytes per complex sample
        
        try:
            # Receive data
            data_bytes = bytearray()
            while len(data_bytes) < bytes_needed:
                chunk = self.socket.recv(min(bytes_needed - len(data_bytes), self.config.buffer_size))
                if not chunk:
                    raise ConnectionError("Connection closed by remote host")
                data_bytes.extend(chunk)
                self.bytes_received += len(chunk)
            
            self.packets_received += 1
            
            # Parse into numpy array
            # Format: interleaved complex samples
            samples = np.frombuffer(data_bytes, dtype=np.float32)
            samples = samples.reshape(-1, 2)  # pairs of real/imag
            complex_samples = samples[:, 0] + 1j * samples[:, 1]
            
            # Reshape to (n_ants, chunk_size)
            data = complex_samples.reshape(n_ants, chunk_size)
            
            return data
            
        except socket.timeout:
            logger.warning("Socket timeout waiting for data")
            raise TimeoutError("Stream timeout - no data received")
        except Exception as e:
            logger.error(f"Error receiving data: {e}")
            raise
    
    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()


class UDPStreamSource(NetworkStreamSource):
    """UDP network streaming source for telescope data.
    
    UDP is commonly used for high-throughput, low-latency streaming
    where occasional packet loss is acceptable.
    """
    
    def connect(self):
        """Setup UDP socket."""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.settimeout(self.config.timeout)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, self.config.buffer_size)
            self.socket.bind((self.config.host, self.config.port))
            
            self.connected = True
            self.start_time = time.time()
            logger.info(f"✓ UDP socket bound to {self.config.host}:{self.config.port}")
            
        except socket.error as e:
            logger.error(f"Failed to bind UDP socket: {e}")
            raise ConnectionError(f"Cannot bind to {self.config.host}:{self.config.port}") from e
    
    def receive_chunk(self, chunk_size: int) -> np.ndarray:
        """Receive data chunk via UDP packets.
        
        Accumulates multiple UDP packets until chunk_size is met.
        """
        if not self.connected:
            raise ConnectionError("UDP socket not bound")
        
        n_ants = self.config.expected_n_ants
        samples_per_packet = 256  # Typical packet size
        packets_needed = int(np.ceil(chunk_size / samples_per_packet))
        
        data_buffer = []
        
        try:
            for _ in range(packets_needed):
                packet, addr = self.socket.recvfrom(65536)  # Max UDP packet size
                self.packets_received += 1
                self.bytes_received += len(packet)
                
                # Parse packet (assume same format as TCP)
                samples = np.frombuffer(packet, dtype=np.float32)
                samples = samples.reshape(-1, 2)
                complex_samples = samples[:, 0] + 1j * samples[:, 1]
                data_buffer.append(complex_samples)
            
            # Concatenate and reshape
            all_samples = np.concatenate(data_buffer)[:chunk_size * n_ants]
            data = all_samples.reshape(n_ants, chunk_size)
            
            return data
            
        except socket.timeout:
            logger.warning("UDP timeout waiting for packets")
            raise TimeoutError("Stream timeout - no packets received")
        except Exception as e:
            logger.error(f"Error receiving UDP data: {e}")
            raise
    
    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()


def create_stream_source(protocol: str, host: str, port: int, **kwargs) -> NetworkStreamSource:
    """Factory function to create appropriate stream source.
    
    Parameters
    ----------
    protocol : str
        'tcp', 'udp', or 'spead'
    host : str
        Hostname or IP address
    port : int
        Port number
    **kwargs
        Additional configuration options
        
    Returns
    -------
    source : NetworkStreamSource
        Configured stream source
        
    Examples
    --------
    >>> source = create_stream_source('tcp', '10.0.0.1', 7148)
    >>> source.connect()
    >>> data = source.receive_chunk(4096)
    >>> source.disconnect()
    """
    config = StreamConfig(protocol=protocol, host=host, port=port, **kwargs)
    
    if protocol == 'tcp':
        return TCPStreamSource(config)
    elif protocol == 'udp':
        return UDPStreamSource(config)
    elif protocol == 'spead':
        # SPEAD protocol - placeholder for future implementation
        logger.warning("SPEAD protocol not yet implemented, falling back to TCP")
        return TCPStreamSource(config)
    else:
        raise ValueError(f"Unknown protocol: {protocol}")


class StreamIterator:
    """Iterator wrapper for streaming data sources.
    
    Provides a convenient interface for processing streaming data in chunks.
    """
    
    def __init__(self, source: NetworkStreamSource, chunk_size: int, max_chunks: Optional[int] = None):
        """Initialize stream iterator.
        
        Parameters
        ----------
        source : NetworkStreamSource
            Connected stream source
        chunk_size : int
            Samples per chunk
        max_chunks : int, optional
            Maximum chunks to yield (None = unlimited)
        """
        self.source = source
        self.chunk_size = chunk_size
        self.max_chunks = max_chunks
        self.chunks_yielded = 0
    
    def __iter__(self):
        """Iterator protocol."""
        return self
    
    def __next__(self) -> np.ndarray:
        """Get next chunk of data."""
        if self.max_chunks and self.chunks_yielded >= self.max_chunks:
            raise StopIteration
        
        try:
            data = self.source.receive_chunk(self.chunk_size)
            self.chunks_yielded += 1
            return data
        except (ConnectionError, TimeoutError) as e:
            logger.warning(f"Stream interrupted: {e}")
            raise StopIteration from e

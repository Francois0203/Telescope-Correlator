"""Unit tests for frontend (data ingestion) module."""
import numpy as np
import pytest
from pathlib import Path
import tempfile
from correlator.frontend import SimulatedStream, BatchFileSource


class TestSimulatedStream:
    """Test simulated streaming data source."""
    
    def test_simulated_stream_initialization(self):
        """Test SimulatedStream can be created."""
        stream = SimulatedStream(
            n_ants=4,
            sample_rate=1024.0,
            source_angles=[0.0, np.pi/4],
            freq=1.0,
            snr=20.0
        )
        assert stream.n_ants == 4
        assert stream.sample_rate == 1024.0
    
    def test_simulated_stream_chunk_shape(self):
        """Test generated chunks have correct shape."""
        stream = SimulatedStream(
            n_ants=3,
            sample_rate=1024.0,
            source_angles=[0.0],
            freq=1.0,
            snr=20.0
        )
        
        chunk_size = 512
        chunks = list(stream.stream(chunk_size=chunk_size, max_chunks=2))
        
        assert len(chunks) == 2
        for chunk in chunks:
            assert chunk.shape == (3, chunk_size)
            assert chunk.dtype == np.complex128
    
    def test_simulated_stream_produces_signal(self):
        """Test that simulated stream produces non-zero signal."""
        stream = SimulatedStream(
            n_ants=2,
            sample_rate=1024.0,
            source_angles=[0.0],
            freq=1.0,
            snr=20.0
        )
        
        chunks = list(stream.stream(chunk_size=256, max_chunks=1))
        chunk = chunks[0]
        
        # Should have non-zero power
        power = np.mean(np.abs(chunk)**2)
        assert power > 0.1
    
    def test_simulated_stream_respects_max_chunks(self):
        """Test that max_chunks limits output."""
        stream = SimulatedStream(
            n_ants=2,
            sample_rate=1024.0,
            source_angles=[0.0],
            freq=1.0,
            snr=20.0
        )
        
        max_chunks = 5
        chunks = list(stream.stream(chunk_size=256, max_chunks=max_chunks))
        
        assert len(chunks) == max_chunks


class TestBatchFileSource:
    """Test batch file data source."""
    
    def test_batch_file_source_loads_file(self):
        """Test BatchFileSource can load a .npy file."""
        # Create temporary file
        with tempfile.NamedTemporaryFile(suffix='.npy', delete=False) as f:
            temp_path = f.name
            data = np.random.randn(4, 2048) + 1j * np.random.randn(4, 2048)
            np.save(temp_path, data)
        
        try:
            source = BatchFileSource(file_path=temp_path, sample_rate=1024.0)
            assert source.n_ants == 4
            assert source.n_samples == 2048
        finally:
            Path(temp_path).unlink()
    
    def test_batch_file_source_chunk_iteration(self):
        """Test BatchFileSource yields correct chunks."""
        with tempfile.NamedTemporaryFile(suffix='.npy', delete=False) as f:
            temp_path = f.name
            data = np.random.randn(3, 1024) + 1j * np.random.randn(3, 1024)
            np.save(temp_path, data)
        
        try:
            source = BatchFileSource(file_path=temp_path, sample_rate=1024.0)
            chunks = list(source.stream(chunk_size=256))
            
            # Should get 4 chunks (1024 / 256)
            assert len(chunks) == 4
            
            for chunk in chunks[:-1]:  # All but last
                assert chunk.shape == (3, 256)
        finally:
            Path(temp_path).unlink()
    
    def test_batch_file_source_rejects_wrong_shape(self):
        """Test BatchFileSource rejects non-2D arrays."""
        with tempfile.NamedTemporaryFile(suffix='.npy', delete=False) as f:
            temp_path = f.name
            data = np.random.randn(4, 3, 256)  # 3D array
            np.save(temp_path, data)
        
        try:
            with pytest.raises(ValueError, match="Expected 2D array"):
                BatchFileSource(file_path=temp_path, sample_rate=1024.0)
        finally:
            Path(temp_path).unlink()

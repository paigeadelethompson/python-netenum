import pytest
import ipaddress
import asyncio
from netenum import netenum, aionetenum

def test_ipv4_enumeration():
    cidrs = ["192.168.0.0/24"]
    addresses = list(netenum(cidrs))
    
    assert len(addresses) == 256
    assert str(addresses[0]) == "192.168.0.0"
    assert str(addresses[-1]) == "192.168.0.255"
    assert all(isinstance(addr, ipaddress.IPv4Address) for addr in addresses)

def test_ipv6_enumeration():
    cidrs = ["2001:db8::/120"]
    addresses = list(netenum(cidrs))
    
    assert len(addresses) == 256
    assert str(addresses[0]) == "2001:db8::"
    assert str(addresses[-1]) == "2001:db8::ff"
    assert all(isinstance(addr, ipaddress.IPv6Address) for addr in addresses)

def test_mixed_enumeration():
    cidrs = ["192.168.0.0/24", "2001:db8::/120"]
    addresses = list(netenum(cidrs))
    
    # Should alternate between IPv4 and IPv6
    assert isinstance(addresses[0], ipaddress.IPv4Address)
    assert isinstance(addresses[1], ipaddress.IPv6Address)
    assert len(addresses) == 512  # 256 from each network

def test_invalid_cidr():
    with pytest.raises(ValueError):
        list(netenum(["invalid"]))

def test_empty_list():
    assert list(netenum([])) == []

@pytest.mark.asyncio(loop_scope="session")
async def test_async_enumeration():
    cidrs = ["192.168.0.0/24"]
    addresses = []
    async for addr in await aionetenum(cidrs):
        addresses.append(addr)
    
    assert len(addresses) == 256
    assert str(addresses[0]) == "192.168.0.0"
    assert str(addresses[-1]) == "192.168.0.255"

def test_large_prefix_memory():
    """Test that large prefixes don't consume excessive memory."""
    import resource
    import gc
    
    # Get initial memory usage
    gc.collect()
    start_mem = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    
    # Enumerate a large network
    cidrs = ["10.0.0.0/8"]  # 16M addresses
    count = 0
    for _ in netenum(cidrs):
        count += 1
        if count >= 1000:  # Just check the first 1000 addresses
            break
    
    # Check memory usage
    gc.collect()
    end_mem = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    
    # Memory increase should be relatively small (less than 10MB)
    assert end_mem - start_mem < 10 * 1024  # 10MB in KB

def test_partition_sizes():
    from netenum.core import determine_partition_size
    
    # Test IPv4 partitioning
    small_net = ipaddress.ip_network("192.168.0.0/24")
    large_net = ipaddress.ip_network("10.0.0.0/8")
    
    assert determine_partition_size(small_net) == 256
    assert determine_partition_size(large_net) >= 256
    
    # Test IPv6 partitioning
    small_v6 = ipaddress.ip_network("2001:db8::/120")
    large_v6 = ipaddress.ip_network("2001:db8::/32")
    
    assert determine_partition_size(small_v6) == 256
    assert determine_partition_size(large_v6) >= 65536 
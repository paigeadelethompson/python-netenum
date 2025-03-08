import asyncio
import ipaddress

import pytest

from netenum import aionetenum, netenum


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
    import gc
    import resource

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


def test_multiple_large_networks_memory():
    """Test memory efficiency when handling multiple large networks simultaneously."""
    import gc
    import resource

    gc.collect()
    start_mem = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss

    # Multiple large networks
    cidrs = ["10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"]  # 16M addresses  # 1M addresses  # 65K addresses

    count = 0
    for _ in netenum(cidrs):
        count += 1
        if count >= 3000:  # Check first 3000 addresses (1000 from each network)
            break

    gc.collect()
    end_mem = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss

    # Memory increase should still be small despite multiple networks
    assert end_mem - start_mem < 15 * 1024  # 15MB in KB
    assert count == 3000


@pytest.mark.asyncio
async def test_async_memory_efficiency():
    """Test memory efficiency during async enumeration."""
    import gc
    import resource

    gc.collect()
    start_mem = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss

    cidrs = ["10.0.0.0/8"]  # 16M addresses
    count = 0

    async for _ in await aionetenum(cidrs):
        count += 1
        if count >= 1000:
            break
        # Simulate some async work
        await asyncio.sleep(0)

    gc.collect()
    end_mem = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss

    # Memory usage should be similar to sync version
    assert end_mem - start_mem < 10 * 1024  # 10MB in KB


def test_partition_scaling():
    """Test that partition sizes scale appropriately with network size."""
    from netenum.core import determine_partition_size

    # Test IPv4 partition scaling
    networks = [
        ("192.168.0.0/24", 256),  # 256 addresses - returns exact size
        ("192.168.0.0/20", 256),  # 4096 addresses - starts with 256
        ("10.0.0.0/8", 1024),  # 16M addresses - scales up to 1024
    ]

    for cidr, expected_partition in networks:
        net = ipaddress.ip_network(cidr)
        size = determine_partition_size(net)
        assert size == expected_partition, f"Partition size {size} != {expected_partition} for {cidr}"
        assert size <= net.num_addresses, f"Partition size {size} too large for {cidr}"


def test_full_range_memory():
    """Test memory efficiency when iterating through a medium-sized range completely."""
    import gc
    import resource

    gc.collect()
    start_mem = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss

    # Use a /16 network (65536 addresses)
    cidrs = ["192.168.0.0/16"]
    count = sum(1 for _ in netenum(cidrs))

    gc.collect()
    end_mem = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss

    # Verify we got all addresses
    assert count == 65536
    # Memory usage should still be reasonable
    assert end_mem - start_mem < 20 * 1024  # 20MB in KB


def test_memory_stability():
    """Test that memory usage remains stable over time."""
    import gc
    import resource

    gc.collect()
    start_mem = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss

    cidrs = ["10.0.0.0/8"]  # 16M addresses
    measurements = []
    count = 0

    # Take memory measurements at different points
    for _ in netenum(cidrs):
        count += 1
        if count % 10000 == 0:
            gc.collect()
            measurements.append(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
        if count >= 50000:
            break

    # Calculate the variation in memory usage
    if measurements:
        variation = max(measurements) - min(measurements)
        # Memory usage should remain relatively stable
        assert variation < 5 * 1024  # 5MB in KB

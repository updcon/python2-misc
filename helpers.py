#!/usr/bin/env python

def get_posixtime(uuid1):
    """
    Converts the uuid1 timestamp to a standard posix timestamp
    """
    assert uuid1.version == 1, ValueError('only applies to type 1')
    t = uuid1.time
    t = t - 0x01b21dd213814000
    t = t / 1e7
    return t
    
def ts_to_isotime(timestamp):
    """
    Converts posix timestamp to human readable ISO format
    """
    from datetime import datetime
    return datetime.isoformat(datetime.fromtimestamp(timestamp))

def ts_to_uuid1(ts):
    """
    Converts posix timestamp in ms to UUID v1
    """
    import time
    import random
    import uuid
    
    nanoseconds = ts * 1e6
    timestamp = int(nanoseconds//100) + 0x01b21dd213814000L

    clock_seq = random.randrange(1<<14L)
    time_low = timestamp & 0xffffffffL
    time_mid = (timestamp >> 32L) & 0xffffL
    time_hi_version = (timestamp >> 48L) & 0x0fffL
    clock_seq_low = clock_seq & 0xffL
    clock_seq_hi_variant = (clock_seq >> 8L) & 0x3fL
    node = uuid.getnode()
    return uuid.UUID(fields=(time_low,
                             time_mid,
                             time_hi_version,
                             clock_seq_hi_variant,
                             clock_seq_low,
                             node),
                     version=1)

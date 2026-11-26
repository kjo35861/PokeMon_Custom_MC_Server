"""Read BMD 1/2 reference geometry bounds without loading game code.

BMD uses big-endian values and null-terminated UTF-16BE strings. Some stock
Pixelmon XZ streams omit their footer: like the Java loader, consume the model
records, while still requiring the complete geometry and no trailing payload.
Coordinates are SMD model space (Z is vertical). Animation poses are not applied.
"""
import lzma
import math
import struct


def model_bounds(data):
    if not data or data[0] not in (1, 2):
        raise ValueError('Unsupported BMD version')
    if data[0] == 2:
        decoder = lzma.LZMADecompressor(format=lzma.FORMAT_XZ)
        payload = decoder.decompress(data[1:], max_length=128 * 1024 * 1024)
        if len(payload) >= 128 * 1024 * 1024 or decoder.unused_data:
            raise ValueError('Invalid BMD compressed payload')
    else:
        payload = data[1:]
    offset = 0

    def take(fmt):
        nonlocal offset
        size = struct.calcsize(fmt)
        if offset + size > len(payload):
            raise ValueError('Truncated BMD record')
        values = struct.unpack_from(fmt, payload, offset)
        offset += size
        return values[0] if len(values) == 1 else values

    def count():
        value = take('>h')
        if value < 0:
            raise ValueError('Negative BMD count')
        return value

    def string():
        while take('>H'):
            pass

    for _ in range(count()):
        take('>hh')
        string()
    for _ in range(count()):
        for _ in range(count()):
            take('>hffffff')
    materials = count()
    for _ in range(materials):
        string()
    low, high = [math.inf] * 3, [-math.inf] * 3
    triangles = count()
    for _ in range(triangles):
        material = take('>b')
        if not 0 <= material < materials:
            raise ValueError('Invalid BMD material')
        for _ in range(3):
            take('>h')
            values = take('>ffffffff')
            if not all(math.isfinite(value) for value in values):
                raise ValueError('Nonfinite BMD geometry')
            for axis, value in enumerate(values[:3]):
                low[axis] = min(low[axis], value)
                high[axis] = max(high[axis], value)
            weights = take('>b')
            if weights < 0:
                raise ValueError('Negative BMD weights')
            for _ in range(weights):
                take('>hf')
    if offset != len(payload) or not triangles:
        raise ValueError('Incomplete or trailing BMD geometry')
    spans = [hi - lo for lo, hi in zip(low, high)]
    if min(spans) <= 0:
        raise ValueError('Degenerate BMD bounds')
    return {'min_xyz': low, 'max_xyz': high, 'span_xyz': spans,
            'height': spans[2], 'triangles': triangles, 'version': data[0]}


def scale_to_height(bounds, target_metres):
    if not math.isfinite(target_metres) or target_metres <= 0:
        raise ValueError('Invalid target height')
    # AbstractPokemonRenderer.scale converts model units to blocks at 1/16.
    # Preserve Pixelmon's separate 1.3 graphics option, Growth and boss factors.
    return target_metres * 16.0 / bounds['height']

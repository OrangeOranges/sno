import re

import pytest
from osgeo import ogr, osr

from sno.gpkg import (
    gpkg_geom_to_hex_wkb,
    gpkg_geom_to_ogr,
    hex_wkb_to_gpkg_geom,
    normalise_gpkg_geom,
    ogr_to_gpkg_geom,
)

SRID_RE = re.compile(r'^SRID=(\d+);(.*)$')


def ewkt_to_ogr(wkt):
    """
    Creates an OGR geometry, optionally with spatial reference,
    from some EWKT.
    """
    m = SRID_RE.match(wkt)
    srid = None
    if m:
        srid, wkt = m.groups()
        srid = int(srid)
    g = ogr.CreateGeometryFromWkt(wkt)
    if srid:
        srs = osr.SpatialReference()
        srs.ImportFromEPSG(srid)
        g.AssignSpatialReference(srs)
    return g


@pytest.mark.parametrize(
    'wkt',
    [
        'POINT(1 2)',
        'POINT(1 2 3)',
        'POINT(1 2 3 4)',
        'POINT EMPTY',
        'SRID=4326;POINT(1 2)',
        'SRID=4326;POINT(1 2 3)',
        'SRID=4326;POINT(1 2 3 4)',
        'SRID=4326;POINT EMPTY',
        'MULTIPOINT EMPTY',
        'MULTIPOINT (1 2)',
        'GEOMETRYCOLLECTION EMPTY',
        'GEOMETRYCOLLECTION (POINT(1 2),MULTIPOINT EMPTY)',
        'TRIANGLE((0 0 0,0 1 0,1 1 0,0 0 0))',
        'TIN (((0 0 0, 0 0 1, 0 1 0, 0 0 0)), ((0 0 0, 0 1 0, 1 1 0, 0 0 0)))',
    ],
)
def test_wkt_gpkg_wkt_roundtrip(wkt):
    orig_ogr_geom = ewkt_to_ogr(wkt)
    gpkg_geom = ogr_to_gpkg_geom(orig_ogr_geom)
    ogr_geom = gpkg_geom_to_ogr(gpkg_geom, parse_srs=True)
    assert ogr_geom.Equals(
        orig_ogr_geom
    ), f'{ogr_geom.ExportToIsoWkt()} != {orig_ogr_geom.ExportToIsoWkt()}'

    orig_srs = orig_ogr_geom.GetSpatialReference()
    srs = ogr_geom.GetSpatialReference()

    if srs or orig_srs:
        assert (
            srs and orig_srs
        ), f'{srs and srs.ExportToProj4()} != {orig_srs and orig_srs.ExportToProj4()}'
        assert srs.ExportToProj4() == orig_srs.ExportToProj4()


@pytest.mark.parametrize(
    'big_endian,little_endian',
    [
        pytest.param(
            # POINT EMPTY (well, POINT(nan nan))
            '00000000017FF80000000000007FF8000000000000',
            '0101000000000000000000F87F000000000000F87F',
            id='point-empty',
        ),
        pytest.param(
            # GEOMETRYCOLLECTION EMPTY
            '000000000700000000',
            '010700000000000000',
            id='geometrycollection-empty',
        ),
        pytest.param(
            # TRIANGLE Z ((0 0 0,0 1 0,1 1 0,0 0 0))
            '00000003F9000000010000000400000000000000000000000000000000000000000000000000000000000000003FF000000000000000000000000000003FF00000000000003FF00000000000000000000000000000000000000000000000000000000000000000000000000000',
            '01F903000001000000040000000000000000000000000000000000000000000000000000000000000000000000000000000000F03F0000000000000000000000000000F03F000000000000F03F0000000000000000000000000000000000000000000000000000000000000000',
            id='triangle',
        ),
        pytest.param(
            # CIRCULARSTRING (1 5,6 2,7 3)
            '0000000008000000033FF0000000000000401400000000000040180000000000004000000000000000401C0000000000004008000000000000',
            '010800000003000000000000000000F03F0000000000001440000000000000184000000000000000400000000000001C400000000000000840',
            id='circularstring',
        ),
    ],
)
def test_wkb_gpkg_wkb_roundtrip(big_endian, little_endian):
    gpkg_geom = hex_wkb_to_gpkg_geom(big_endian)

    assert gpkg_geom_to_hex_wkb(gpkg_geom) == little_endian


@pytest.mark.parametrize(
    'input,input_has_envelope',
    [
        # These geometries are little-endian with no envelope
        pytest.param(
            # POINT EMPTY (well, 'POINT(nan nan)')
            b'GP\x00\x01\x00\x00\x00\x00\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
            False,
            id='point-empty',
        ),
        pytest.param(
            # POINT(5 5)
            b'GP\x00\x01\x00\x00\x00\x00\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x14@\x00\x00\x00\x00\x00\x00\x14@',
            False,
            id='point',
        ),
        pytest.param(
            # POLYGON((0 0,0 5,5 0,0 0))
            b'GP\x00\x03\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x14@\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x14@\x01\x03\x00\x00\x00\x01\x00\x00\x00\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x14@\x00\x00\x00\x00\x00\x00\x14@\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
            True,
            id='polygon',
        ),
    ],
)
@pytest.mark.parametrize('little_endian', [False, True])
@pytest.mark.parametrize('little_endian_wkb', [False, True])
@pytest.mark.parametrize('with_envelope', [False, True])
def test_gpkg_wkb_gpkg_roundtrip(
    input, input_has_envelope, little_endian, little_endian_wkb, with_envelope
):
    """
    Tests the following functions work and are consistent with each other:
        * normalise_gpkg_geom
        * gpkg_geom_to_hex_wkb
        * hex_wkb_to_gpkg_geom
    """
    assert normalise_gpkg_geom(input) == input
    hex_wkb = gpkg_geom_to_hex_wkb(input)
    assert hex_wkb.startswith('01'), "gpkg_geom_to_hex_wkb produced big-endian WKB"

    # Produce a GPKG geom in LE/BE variants of both the GPKG headers and the WKB itself.
    gpkg_geom_intermediate = hex_wkb_to_gpkg_geom(
        hex_wkb,
        _little_endian=little_endian,
        _little_endian_wkb=little_endian_wkb,
        _add_envelope=with_envelope,
    )
    assert normalise_gpkg_geom(gpkg_geom_intermediate) == input

    if little_endian and little_endian_wkb and with_envelope == input_has_envelope:
        assert gpkg_geom_intermediate == input
        return
    else:
        if with_envelope and not input_has_envelope:
            # If we're adding an envelope, the geometry should have gotten bigger...
            assert len(gpkg_geom_intermediate) > len(input)
        elif input_has_envelope and not with_envelope:
            # If we're removing an envelope, the geometry should have gotten smaller...
            assert len(gpkg_geom_intermediate) < len(input)
        else:
            assert len(gpkg_geom_intermediate) == len(input)

    # Now re-roundtrip to convert it back to the original
    # (little-endian, no envelope)
    hex_wkb_2 = gpkg_geom_to_hex_wkb(gpkg_geom_intermediate)
    gpkg_geom = hex_wkb_to_gpkg_geom(hex_wkb_2)

    assert gpkg_geom == input

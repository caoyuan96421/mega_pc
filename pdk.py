import gdsfactory as gf


class LAYERS(gf.technology.LayerMap):
    DUMMY: gf.typings.Layer = (0, 0)
    DEVICE: gf.typings.Layer = (1, 0)
    DEVICE_REMOVE: gf.typings.Layer = (2, 0)

    HANDLE_P0: gf.typings.Layer = (11, 0)
    HANDLE_P1: gf.typings.Layer = (11, 1)
    HANDLE_P2: gf.typings.Layer = (11, 2)
    HANDLE_P3: gf.typings.Layer = (11, 3)
    HANDLE_P4: gf.typings.Layer = (11, 4)
    HANDLE_P5: gf.typings.Layer = (11, 5)
    HANDLE_P6: gf.typings.Layer = (11, 6)
    HANDLE_P7: gf.typings.Layer = (11, 7)
    HANDLE_REMOVE: gf.typings.Layer = (12, 0)

    VIAS_ETCH: gf.typings.Layer = (21, 0)
    POLY: gf.typings.Layer = (22, 0)
    OXIDE: gf.typings.Layer = (23, 0)
    NITRIDE: gf.typings.Layer = (24, 0)

    CAP_OXIDE: gf.typings.Layer = (101, 0)
    CAP_NITRIDE: gf.typings.Layer = (102, 0)
    CAP_BOND: gf.typings.Layer = (103, 0)
    CAP_TRENCH_ETCH: gf.typings.Layer = (104, 0)
    CAP_BACKSIDE: gf.typings.Layer = (105, 0)


PDK = gf.Pdk(
    name="mega_pc",
    layers=LAYERS,
    layer_views=gf.technology.LayerViews(),
)

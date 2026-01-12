import gdsfactory as gf

gf.clear_cache()


import gfelib as gl
import gfebuild as gb
import sys
import datetime
import argparse

from pdk import LAYERS, PDK
from device import device, CHIP_SIZE, CAVITY_WIDTH

PDK.activate()

parser = argparse.ArgumentParser(description="Build script for MEGA-PC")
parser.add_argument(
    "--no-merge",
    action="store_true",
    help="Don't merge the device patterns (e.g. release holes), because it can be very slow. For debug use only, ASML reticle files will not be generated",
)
parser.add_argument(
    "--mirror",
    action="store_true",
    help="Write additional ASML reticle files that are mirrored across x=0 (PLACEMENTS file is not mirrored)",
)
parser.add_argument(
    "--show",
    action="store_true",
    help="Show the last pattern with KLayout",
)
parser.add_argument(
    "--version",
    action="store",
    type=str,
    help="Add version number text",
    required=True,
)
parser.add_argument(
    "--hash",
    action="store",
    type=str,
    help="Add hash text",
    default="",
)

args = parser.parse_args()

date_str = str(datetime.date.today())

WAFER_DIAMETER = 150000
WAFER_ALIGNMENT_MARKS = [
    (-40000, 2000),
    (40000, 2000),
    (-40000, -2000),
    (40000, -2000),
    (-8000, 48000),
    (8000, 48000),
]

CHIP_RECT = gf.components.rectangle(
    size=(CHIP_SIZE, CHIP_SIZE),
    layer=LAYERS.DUMMY,
    centered=True,
)

d = device(text=f"{args.version}\n{args.hash[:7]}\n{date_str}")

d.write_gds(f"./build/mega_pc_{args.version}_SOURCE.gds")

c = gf.Component(name="chip")

if not args.no_merge:
    # DEVICE merged
    _ = c << gf.boolean(
        A=gf.boolean(
            A=CHIP_RECT,
            B=d,
            operation="-",
            layer=LAYERS.DUMMY,
            layer1=LAYERS.DUMMY,
            layer2=LAYERS.DEVICE,
        ),
        B=d,
        operation="|",
        layer=LAYERS.DEVICE_REMOVE,
        layer1=LAYERS.DUMMY,
        layer2=LAYERS.DEVICE_REMOVE,
    )
else:
    # DEVICE and DEVICE_REMOVE not merged
    _ = c << d.extract(layers=[LAYERS.DEVICE, LAYERS.DEVICE_REMOVE])

# HANDLE
handle = gf.Component()

for i in range(7, -1, -1):
    handle = gf.boolean(
        A=handle,
        B=d,
        operation="-",
        layer=LAYERS.DUMMY,
        layer1=LAYERS.DUMMY,
        layer2=(LAYERS.HANDLE_P0[0], i),
    )

    exp = gf.boolean(
        A=gf.Component(),
        B=d,
        operation="|",
        layer=LAYERS.DUMMY,
        layer1=LAYERS.DUMMY,
        layer2=(LAYERS.HANDLE_P0[0], i),
    )
    exp.offset(layer=LAYERS.DUMMY, distance=CAVITY_WIDTH)

    border = gf.boolean(
        A=exp,
        B=d,
        operation="-",
        layer=LAYERS.DUMMY,
        layer1=LAYERS.DUMMY,
        layer2=(LAYERS.HANDLE_P0[0], i),
    )

    handle = gf.boolean(
        A=handle,
        B=border,
        operation="|",
        layer=LAYERS.DUMMY,
        layer1=LAYERS.DUMMY,
        layer2=LAYERS.DUMMY,
    )

_ = c << gf.boolean(
    A=handle,
    B=d,
    operation="|",
    layer=LAYERS.HANDLE_REMOVE,
    layer1=LAYERS.DUMMY,
    layer2=LAYERS.HANDLE_REMOVE,
)


# POSITIVE LAYERS
for layer in [
    LAYERS.VIAS_ETCH,
    LAYERS.CAP_TRENCH_ETCH,
    LAYERS.CAP_BACKSIDE,
]:
    _ = c << gf.boolean(
        A=CHIP_RECT,
        B=d,
        operation="&",
        layer=layer,
        layer1=LAYERS.DUMMY,
        layer2=layer,
    )

# NEGATIVE LAYERS
for layer in [
    LAYERS.POLY,
    LAYERS.OXIDE,
    LAYERS.NITRIDE,
    LAYERS.CAP_OXIDE,
    LAYERS.CAP_NITRIDE,
    LAYERS.CAP_BOND,
]:
    _ = c << gf.boolean(
        A=CHIP_RECT,
        B=d,
        operation="-",
        layer=layer,
        layer1=LAYERS.DUMMY,
        layer2=layer,
    )

# PROCESS COMPENSATION

# DRIE expands all features by 0.3 um
c.offset(layer=LAYERS.DEVICE_REMOVE, distance=-0.3)
c.offset(layer=LAYERS.HANDLE_REMOVE, distance=-0.3)

c.flatten()
c.write_gds(f"./build/mega_pc_{args.version}_BUILD.gds", with_metadata=False)

if not args.no_merge:
    # generate reticles
    reticles, placements = gb.asml300.reticle(
        component=c,
        image_size=(CHIP_SIZE, CHIP_SIZE),
        image_layers=[
            LAYERS.VIAS_ETCH,
            LAYERS.POLY,
            LAYERS.OXIDE,
            LAYERS.NITRIDE,
            LAYERS.DEVICE_REMOVE,
            LAYERS.CAP_OXIDE,
            LAYERS.CAP_NITRIDE,
            LAYERS.CAP_BOND,
        ],
        id=f"MPC-{args.version}",
        text=date_str,
    )

    for i, reticle in enumerate(reticles):
        for key, value in placements.items():
            if value[0] == i:
                _ = reticle << gf.components.text(
                    text=str(LAYERS(key)),
                    size=0.2 * CHIP_SIZE,
                    position=(value[1], value[2]),
                    justify="center",
                    layer=LAYERS.DUMMY,
                )
        reticle.flatten()
        reticle.write_gds(
            f"./build/mega_pc_{args.version}_BUILD_ASML_{i}.gds", with_metadata=False
        )

        if args.mirror:
            reticle.mirror_x(0)
            reticle.write_gds(
                f"./build/mega_pc_{args.version}_BUILD_ASML_{i}_MIRROR.gds",
                with_metadata=False,
            )

    with open(f"./build/mega_pc_{args.version}_BUILD_ASML_PLACEMENTS.txt", "w") as f:
        for key, value in placements.items():
            f.write(f"{LAYERS(key)}: {value[0]}, {value[1]:.2f}, {value[2]:.2f}\n")

    # generate wafer masks for backside
    for layer in [
        LAYERS.HANDLE_REMOVE,
        LAYERS.CAP_TRENCH_ETCH,
        LAYERS.CAP_BACKSIDE,
    ]:
        wafer, placements = gb.asml300.wafer(
            radius=0.5 * WAFER_DIAMETER,
            chip_center=True,
            place_partial=False,
            marks=WAFER_ALIGNMENT_MARKS,
            component=c,
            image_size=(CHIP_SIZE, CHIP_SIZE),
            image_layer=layer,
            id=f"MPC-{args.version}-{LAYERS(layer)}",
            text=date_str,
        )
        wafer.write_gds(
            f"./build/mega_pc_{args.version}_BUILD_WAFER_{LAYERS(layer)}.gds",
            with_metadata=False,
        )

        if args.mirror:
            wafer.mirror_x(0)
            wafer.write_gds(
                f"./build/mega_pc_{args.version}_BUILD_WAFER_{LAYERS(layer)}_MIRROR.gds",
                with_metadata=False,
            )

        with open(
            f"./build/mega_pc_{args.version}_BUILD_WAFER_{LAYERS(layer)}_PLACEMENTS.txt",
            "w",
        ) as f:
            f.write(f"WAFER_DIAMETER: {WAFER_DIAMETER:.2f}\n")
            f.write(f"X_STEP_SIZE: {CHIP_SIZE:.2f}\n")
            f.write(f"Y_STEP_SIZE: {CHIP_SIZE:.2f}\n")
            f.write(f"CHIP_COUNT: {len(placements)}\n")
            f.write(f"\n")
            for mark in WAFER_ALIGNMENT_MARKS:
                f.write(f"MARK: {mark[0]:.2f}, {mark[1]:.2f}\n")
            f.write(f"\n")
            for placement in placements:
                f.write(f"CHIP: {placement[0]:.2f}, {placement[1]:.2f}\n")


if args.show:
    c.show()

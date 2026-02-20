import bpy
import math
import os


def clean_scene():
    """Reset Blender to empty state."""
    bpy.ops.wm.read_factory_settings(use_empty=True)


def make_mat(name, color):
    """Create a Principled BSDF material with the given RGBA color."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = color
    bsdf.inputs["Roughness"].default_value = 0.8
    return mat


def add_mesh(name, prim_fn, mat, loc, scale, rot=(0, 0, 0)):
    """Add a primitive mesh with material at the given location/scale/rotation."""
    prim_fn()
    obj = bpy.context.active_object
    obj.name = name
    obj.location = loc
    obj.scale = scale
    obj.rotation_euler = rot
    obj.data.materials.append(mat)
    return obj


def setup_render(scene, width=1280, height=720):
    """Configure EEVEE rendering with dark background."""
    scene.render.engine = 'BLENDER_EEVEE'
    scene.render.resolution_x = width
    scene.render.resolution_y = height
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.world = bpy.data.worlds.new("World")
    scene.world.use_nodes = True
    bg = scene.world.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (0.15, 0.12, 0.08, 1)
    bg.inputs["Strength"].default_value = 1.0


def setup_camera(scene, loc, target_loc, lens=28):
    """Add camera with TRACK_TO constraint aimed at target location."""
    bpy.ops.object.camera_add(location=loc)
    camera = bpy.context.active_object
    scene.camera = camera
    bpy.ops.object.empty_add(location=target_loc)
    target = bpy.context.active_object
    target.name = "CamTarget"
    track = camera.constraints.new(type='TRACK_TO')
    track.target = target
    track.track_axis = 'TRACK_NEGATIVE_Z'
    track.up_axis = 'UP_Y'
    camera.data.lens = lens
    return camera


def add_light(scene):
    """Add key light (sun) and fill light (point)."""
    bpy.ops.object.light_add(type='SUN', location=(5, -5, 10))
    sun = bpy.context.active_object
    sun.data.energy = 5
    sun.data.color = (1.0, 0.9, 0.7)
    sun.rotation_euler = (math.radians(45), 0, math.radians(30))
    bpy.ops.object.light_add(type='POINT', location=(-5, 3, 5))
    fill = bpy.context.active_object
    fill.data.energy = 200
    fill.data.color = (0.7, 0.7, 0.9)


def add_ground(mat, size=15):
    """Add a ground plane."""
    add_mesh("Floor", bpy.ops.mesh.primitive_plane_add, mat, (0, 0, 0), (size, size, 1))


def build_large_figure(name, mat, position, pose="standing"):
    """Build a large/heavy character from primitives (gorilla-like proportions).

    Args:
        name: Character name prefix for objects
        mat: Blender material to apply
        position: (x, y, z) base position — z is ground level
        pose: one of "standing", "arms_raised", "fighting_stance", "fallen", "seated"
    """
    x, y, z = position

    if pose == "fallen":
        # Toppled sideways on ground
        add_mesh(f"{name}_Body", bpy.ops.mesh.primitive_cube_add, mat,
                 (x, y, z + 0.3), (0.6, 0.4, 0.7),
                 rot=(math.radians(75), 0, math.radians(10)))
        add_mesh(f"{name}_Head", bpy.ops.mesh.primitive_uv_sphere_add, mat,
                 (x + 1.0, y - 0.4, z + 0.18), (0.35, 0.3, 0.3),
                 rot=(math.radians(40), math.radians(35), 0))
        add_mesh(f"{name}_Arm", bpy.ops.mesh.primitive_cylinder_add, mat,
                 (x - 0.6, y + 0.6, z + 0.12), (0.14, 0.14, 0.5),
                 rot=(math.radians(90), 0, math.radians(25)))
        add_mesh(f"{name}_Leg", bpy.ops.mesh.primitive_cylinder_add, mat,
                 (x + 0.5, y - 0.7, z + 0.1), (0.15, 0.15, 0.45),
                 rot=(math.radians(85), 0, math.radians(-30)))
        return

    # Upright poses
    add_mesh(f"{name}_Body", bpy.ops.mesh.primitive_cube_add, mat,
             (x, y, z + 1.1), (0.65, 0.45, 0.75))
    add_mesh(f"{name}_Head", bpy.ops.mesh.primitive_uv_sphere_add, mat,
             (x, y, z + 2.2), (0.38, 0.33, 0.33))

    # Legs (always planted)
    add_mesh(f"{name}_LegL", bpy.ops.mesh.primitive_cylinder_add, mat,
             (x - 0.4, y, z + 0.0), (0.16, 0.16, 0.45))
    add_mesh(f"{name}_LegR", bpy.ops.mesh.primitive_cylinder_add, mat,
             (x + 0.4, y, z + 0.0), (0.16, 0.16, 0.45))

    if pose == "arms_raised":
        add_mesh(f"{name}_ArmL", bpy.ops.mesh.primitive_cylinder_add, mat,
                 (x - 0.8, y, z + 2.4), (0.14, 0.14, 0.55),
                 rot=(0, math.radians(30), math.radians(-20)))
        add_mesh(f"{name}_ArmR", bpy.ops.mesh.primitive_cylinder_add, mat,
                 (x + 0.8, y, z + 2.4), (0.14, 0.14, 0.55),
                 rot=(0, math.radians(-30), math.radians(20)))
    elif pose == "fighting_stance":
        add_mesh(f"{name}_ArmL", bpy.ops.mesh.primitive_cylinder_add, mat,
                 (x - 0.7, y - 0.3, z + 1.5), (0.14, 0.14, 0.45),
                 rot=(math.radians(-45), 0, math.radians(-15)))
        add_mesh(f"{name}_ArmR", bpy.ops.mesh.primitive_cylinder_add, mat,
                 (x + 0.7, y - 0.3, z + 1.5), (0.14, 0.14, 0.45),
                 rot=(math.radians(-45), 0, math.radians(15)))
    elif pose == "seated":
        add_mesh(f"{name}_ArmL", bpy.ops.mesh.primitive_cylinder_add, mat,
                 (x - 0.7, y, z + 0.85), (0.14, 0.14, 0.5))
        add_mesh(f"{name}_ArmR", bpy.ops.mesh.primitive_cylinder_add, mat,
                 (x + 0.7, y, z + 0.85), (0.14, 0.14, 0.5))
    else:  # standing
        add_mesh(f"{name}_ArmL", bpy.ops.mesh.primitive_cylinder_add, mat,
                 (x - 0.7, y, z + 0.85), (0.14, 0.14, 0.5))
        add_mesh(f"{name}_ArmR", bpy.ops.mesh.primitive_cylinder_add, mat,
                 (x + 0.7, y, z + 0.85), (0.14, 0.14, 0.5))


def build_regular_male(name, mat, position, pose="standing"):
    """Build a regular male character from primitives.

    Args:
        name: Character name prefix for objects
        mat: Blender material to apply
        position: (x, y, z) base position — z is ground level
        pose: one of "standing", "arms_raised", "fighting_stance", "fallen", "seated"
    """
    x, y, z = position

    if pose == "fallen":
        add_mesh(f"{name}_Body", bpy.ops.mesh.primitive_cube_add, mat,
                 (x, y, z + 0.25), (0.4, 0.3, 0.55),
                 rot=(math.radians(80), 0, math.radians(15)))
        add_mesh(f"{name}_Head", bpy.ops.mesh.primitive_cube_add, mat,
                 (x + 0.8, y - 0.3, z + 0.15), (0.2, 0.18, 0.2),
                 rot=(math.radians(40), math.radians(30), 0))
        add_mesh(f"{name}_Arm", bpy.ops.mesh.primitive_cylinder_add, mat,
                 (x - 0.5, y + 0.4, z + 0.1), (0.1, 0.1, 0.4),
                 rot=(math.radians(90), 0, math.radians(20)))
        add_mesh(f"{name}_Leg", bpy.ops.mesh.primitive_cylinder_add, mat,
                 (x + 0.4, y - 0.5, z + 0.08), (0.1, 0.1, 0.4),
                 rot=(math.radians(85), 0, math.radians(-25)))
        return

    # Upright poses
    add_mesh(f"{name}_Body", bpy.ops.mesh.primitive_cube_add, mat,
             (x, y, z + 0.9), (0.4, 0.3, 0.55))
    add_mesh(f"{name}_Head", bpy.ops.mesh.primitive_cube_add, mat,
             (x, y, z + 1.7), (0.2, 0.18, 0.2))

    # Legs
    add_mesh(f"{name}_LegL", bpy.ops.mesh.primitive_cylinder_add, mat,
             (x - 0.25, y, z + 0.0), (0.1, 0.1, 0.4))
    add_mesh(f"{name}_LegR", bpy.ops.mesh.primitive_cylinder_add, mat,
             (x + 0.25, y, z + 0.0), (0.1, 0.1, 0.4))

    if pose == "arms_raised":
        add_mesh(f"{name}_ArmL", bpy.ops.mesh.primitive_cylinder_add, mat,
                 (x - 0.6, y, z + 2.0), (0.1, 0.1, 0.45),
                 rot=(0, math.radians(25), math.radians(-20)))
        add_mesh(f"{name}_ArmR", bpy.ops.mesh.primitive_cylinder_add, mat,
                 (x + 0.6, y, z + 2.0), (0.1, 0.1, 0.45),
                 rot=(0, math.radians(-25), math.radians(20)))
    elif pose == "fighting_stance":
        add_mesh(f"{name}_ArmL", bpy.ops.mesh.primitive_cylinder_add, mat,
                 (x - 0.5, y - 0.3, z + 1.2), (0.1, 0.1, 0.35),
                 rot=(math.radians(-50), 0, math.radians(-10)))
        add_mesh(f"{name}_ArmR", bpy.ops.mesh.primitive_cylinder_add, mat,
                 (x + 0.5, y - 0.3, z + 1.2), (0.1, 0.1, 0.35),
                 rot=(math.radians(-50), 0, math.radians(10)))
    else:  # standing, seated
        add_mesh(f"{name}_ArmL", bpy.ops.mesh.primitive_cylinder_add, mat,
                 (x - 0.5, y, z + 0.7), (0.1, 0.1, 0.4))
        add_mesh(f"{name}_ArmR", bpy.ops.mesh.primitive_cylinder_add, mat,
                 (x + 0.5, y, z + 0.7), (0.1, 0.1, 0.4))


def build_regular_female(name, mat, position, pose="standing"):
    """Build a regular female character from primitives.

    Args:
        name: Character name prefix for objects
        mat: Blender material to apply
        position: (x, y, z) base position — z is ground level
        pose: one of "standing", "arms_raised", "fighting_stance", "fallen", "seated"
    """
    x, y, z = position

    if pose == "fallen":
        add_mesh(f"{name}_Body", bpy.ops.mesh.primitive_cube_add, mat,
                 (x, y, z + 0.22), (0.35, 0.25, 0.5),
                 rot=(math.radians(80), 0, math.radians(15)))
        add_mesh(f"{name}_Head", bpy.ops.mesh.primitive_uv_sphere_add, mat,
                 (x + 0.7, y - 0.3, z + 0.15), (0.18, 0.16, 0.18),
                 rot=(math.radians(40), math.radians(30), 0))
        return

    # Upright poses — slightly narrower/shorter than male
    add_mesh(f"{name}_Body", bpy.ops.mesh.primitive_cube_add, mat,
             (x, y, z + 0.85), (0.35, 0.25, 0.5))
    add_mesh(f"{name}_Head", bpy.ops.mesh.primitive_uv_sphere_add, mat,
             (x, y, z + 1.55), (0.18, 0.16, 0.18))

    # Legs
    add_mesh(f"{name}_LegL", bpy.ops.mesh.primitive_cylinder_add, mat,
             (x - 0.2, y, z + 0.0), (0.09, 0.09, 0.38))
    add_mesh(f"{name}_LegR", bpy.ops.mesh.primitive_cylinder_add, mat,
             (x + 0.2, y, z + 0.0), (0.09, 0.09, 0.38))

    if pose == "arms_raised":
        add_mesh(f"{name}_ArmL", bpy.ops.mesh.primitive_cylinder_add, mat,
                 (x - 0.5, y, z + 1.8), (0.08, 0.08, 0.4),
                 rot=(0, math.radians(25), math.radians(-20)))
        add_mesh(f"{name}_ArmR", bpy.ops.mesh.primitive_cylinder_add, mat,
                 (x + 0.5, y, z + 1.8), (0.08, 0.08, 0.4),
                 rot=(0, math.radians(-25), math.radians(20)))
    elif pose == "fighting_stance":
        add_mesh(f"{name}_ArmL", bpy.ops.mesh.primitive_cylinder_add, mat,
                 (x - 0.45, y - 0.25, z + 1.1), (0.08, 0.08, 0.32),
                 rot=(math.radians(-50), 0, math.radians(-10)))
        add_mesh(f"{name}_ArmR", bpy.ops.mesh.primitive_cylinder_add, mat,
                 (x + 0.45, y - 0.25, z + 1.1), (0.08, 0.08, 0.32),
                 rot=(math.radians(-50), 0, math.radians(10)))
    else:  # standing, seated
        add_mesh(f"{name}_ArmL", bpy.ops.mesh.primitive_cylinder_add, mat,
                 (x - 0.45, y, z + 0.65), (0.08, 0.08, 0.38))
        add_mesh(f"{name}_ArmR", bpy.ops.mesh.primitive_cylinder_add, mat,
                 (x + 0.45, y, z + 0.65), (0.08, 0.08, 0.38))


# === SCENE SETUP ===

clean_scene()
scene = bpy.context.scene
setup_render(scene)
add_light(scene)

# Materials
mat_ground = make_mat("Ground", (0.2, 0.15, 0.1, 1))
mat_gale = make_mat("Gale", (0.5, 0.2, 0.2, 1))
mat_truck_body = make_mat("TruckBody", (0.35, 0.25, 0.15, 1))
mat_truck_cab = make_mat("TruckCab", (0.3, 0.22, 0.12, 1))
mat_truck_wheel = make_mat("TruckWheel", (0.08, 0.08, 0.08, 1))
mat_truck_bumper = make_mat("TruckBumper", (0.15, 0.15, 0.15, 1))
mat_road = make_mat("Road", (0.12, 0.1, 0.08, 1))

# Ground
add_ground(mat_ground)

# Desert road surface
add_mesh("Road", bpy.ops.mesh.primitive_cube_add, mat_road,
         (0, 0, 0.01), (3, 12, 0.01))

# === GALE — fallen on the ground, pushing up, looking to the side ===
build_regular_female("Gale", mat_gale, (0, 0, 0), pose="fallen")

# Add her arms in a pushing-up position (the fallen pose only has body+head)
add_mesh("Gale_ArmL", bpy.ops.mesh.primitive_cylinder_add, mat_gale,
         (-0.4, 0.2, 0.12), (0.08, 0.08, 0.35),
         rot=(math.radians(60), 0, math.radians(-20)))
add_mesh("Gale_ArmR", bpy.ops.mesh.primitive_cylinder_add, mat_gale,
         (0.4, 0.2, 0.12), (0.08, 0.08, 0.35),
         rot=(math.radians(60), 0, math.radians(20)))
# Legs sprawled behind
add_mesh("Gale_LegL", bpy.ops.mesh.primitive_cylinder_add, mat_gale,
         (-0.3, -0.5, 0.06), (0.09, 0.09, 0.42),
         rot=(math.radians(88), 0, math.radians(-10)))
add_mesh("Gale_LegR", bpy.ops.mesh.primitive_cylinder_add, mat_gale,
         (0.25, -0.6, 0.06), (0.09, 0.09, 0.42),
         rot=(math.radians(85), 0, math.radians(15)))

# === CAB-OVER TRUCK behind Gale ===
tx, ty, tz = 0, 3.0, 0

# Cab (tall box, cab-over style — cab sits above front axle)
add_mesh("Truck_Cab", bpy.ops.mesh.primitive_cube_add, mat_truck_cab,
         (tx, ty - 0.5, tz + 1.8), (1.2, 0.8, 1.0))

# Windshield area (slightly darker inset)
add_mesh("Truck_Windshield", bpy.ops.mesh.primitive_cube_add, mat_truck_bumper,
         (tx, ty - 1.35, tz + 2.0), (0.95, 0.02, 0.5))

# Cargo bed (longer, lower box behind cab)
add_mesh("Truck_Bed", bpy.ops.mesh.primitive_cube_add, mat_truck_body,
         (tx, ty + 1.8, tz + 1.3), (1.3, 2.0, 0.7))

# Front bumper
add_mesh("Truck_Bumper", bpy.ops.mesh.primitive_cube_add, mat_truck_bumper,
         (tx, ty - 1.3, tz + 0.5), (1.3, 0.15, 0.25))

# Undercarriage
add_mesh("Truck_Under", bpy.ops.mesh.primitive_cube_add, mat_truck_bumper,
         (tx, ty + 0.8, tz + 0.35), (1.0, 2.8, 0.2))

# Wheels — front pair
add_mesh("Truck_WheelFL", bpy.ops.mesh.primitive_cylinder_add, mat_truck_wheel,
         (tx - 1.25, ty - 0.6, tz + 0.35), (0.35, 0.35, 0.15),
         rot=(0, math.radians(90), 0))
add_mesh("Truck_WheelFR", bpy.ops.mesh.primitive_cylinder_add, mat_truck_wheel,
         (tx + 1.25, ty - 0.6, tz + 0.35), (0.35, 0.35, 0.15),
         rot=(0, math.radians(90), 0))

# Wheels — rear pair
add_mesh("Truck_WheelRL", bpy.ops.mesh.primitive_cylinder_add, mat_truck_wheel,
         (tx - 1.25, ty + 2.5, tz + 0.35), (0.35, 0.35, 0.15),
         rot=(0, math.radians(90), 0))
add_mesh("Truck_WheelRR", bpy.ops.mesh.primitive_cylinder_add, mat_truck_wheel,
         (tx + 1.25, ty + 2.5, tz + 0.35), (0.35, 0.35, 0.15),
         rot=(0, math.radians(90), 0))

# === CAMERA — low angle, ground level, looking up at Gale and truck ===
setup_camera(scene,
             loc=(1.5, -4.0, 0.35),
             target_loc=(0, 0.5, 0.4),
             lens=24)

# === RENDER ===
scene.frame_set(1)
scene.render.filepath = "/Users/jmordetsky/directors-chair/assets/generated/videos/raider_ambush_v2/layouts/layout_020.png"
bpy.ops.render.render(write_still=True)
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
    """Build a large/heavy character from primitives (gorilla-like proportions)."""
    x, y, z = position

    if pose == "fallen":
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

    add_mesh(f"{name}_Body", bpy.ops.mesh.primitive_cube_add, mat,
             (x, y, z + 1.1), (0.65, 0.45, 0.75))
    add_mesh(f"{name}_Head", bpy.ops.mesh.primitive_uv_sphere_add, mat,
             (x, y, z + 2.2), (0.38, 0.33, 0.33))

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
    else:
        add_mesh(f"{name}_ArmL", bpy.ops.mesh.primitive_cylinder_add, mat,
                 (x - 0.7, y, z + 0.85), (0.14, 0.14, 0.5))
        add_mesh(f"{name}_ArmR", bpy.ops.mesh.primitive_cylinder_add, mat,
                 (x + 0.7, y, z + 0.85), (0.14, 0.14, 0.5))


def build_regular_male(name, mat, position, pose="standing"):
    """Build a regular male character from primitives."""
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

    add_mesh(f"{name}_Body", bpy.ops.mesh.primitive_cube_add, mat,
             (x, y, z + 0.9), (0.4, 0.3, 0.55))
    add_mesh(f"{name}_Head", bpy.ops.mesh.primitive_cube_add, mat,
             (x, y, z + 1.7), (0.2, 0.18, 0.2))

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
    else:
        add_mesh(f"{name}_ArmL", bpy.ops.mesh.primitive_cylinder_add, mat,
                 (x - 0.5, y, z + 0.7), (0.1, 0.1, 0.4))
        add_mesh(f"{name}_ArmR", bpy.ops.mesh.primitive_cylinder_add, mat,
                 (x + 0.5, y, z + 0.7), (0.1, 0.1, 0.4))


def build_regular_female(name, mat, position, pose="standing"):
    """Build a regular female character from primitives."""
    x, y, z = position

    if pose == "fallen":
        add_mesh(f"{name}_Body", bpy.ops.mesh.primitive_cube_add, mat,
                 (x, y, z + 0.22), (0.35, 0.25, 0.5),
                 rot=(math.radians(80), 0, math.radians(15)))
        add_mesh(f"{name}_Head", bpy.ops.mesh.primitive_uv_sphere_add, mat,
                 (x + 0.7, y - 0.3, z + 0.15), (0.18, 0.16, 0.18),
                 rot=(math.radians(40), math.radians(30), 0))
        return

    add_mesh(f"{name}_Body", bpy.ops.mesh.primitive_cube_add, mat,
             (x, y, z + 0.85), (0.35, 0.25, 0.5))
    add_mesh(f"{name}_Head", bpy.ops.mesh.primitive_uv_sphere_add, mat,
             (x, y, z + 1.55), (0.18, 0.16, 0.18))

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
    else:
        add_mesh(f"{name}_ArmL", bpy.ops.mesh.primitive_cylinder_add, mat,
                 (x - 0.45, y, z + 0.65), (0.08, 0.08, 0.38))
        add_mesh(f"{name}_ArmR", bpy.ops.mesh.primitive_cylinder_add, mat,
                 (x + 0.45, y, z + 0.65), (0.08, 0.08, 0.38))


# --- Scene Setup ---
clean_scene()
scene = bpy.context.scene
setup_render(scene)
add_light(scene)

# Materials
gorilla_mat = make_mat("Gorilla", (0.25, 0.18, 0.1, 1))
zombie_mat = make_mat("Zombie", (0.6, 0.6, 0.65, 1))
ground_mat = make_mat("Ground", (0.2, 0.15, 0.1, 1))
jeep_body_mat = make_mat("JeepBody", (0.22, 0.28, 0.18, 1))
jeep_wheel_mat = make_mat("JeepWheel", (0.08, 0.08, 0.08, 1))
jeep_frame_mat = make_mat("JeepFrame", (0.15, 0.15, 0.12, 1))
road_mat = make_mat("Road", (0.12, 0.1, 0.08, 1))
bat_mat = make_mat("Bat", (0.45, 0.3, 0.15, 1))

# Ground — desert sand
add_ground(ground_mat, size=30)

# Desert highway — long dark strip running along Y axis
add_mesh("Road", bpy.ops.mesh.primitive_cube_add, road_mat,
         (0, 5, 0.01), (2.5, 25, 0.01))

# Road center line dashes
line_mat = make_mat("RoadLine", (0.7, 0.65, 0.4, 1))
for i in range(-8, 20, 3):
    add_mesh(f"Line_{i}", bpy.ops.mesh.primitive_cube_add, line_mat,
             (0, float(i), 0.02), (0.06, 0.8, 0.005))

# --- Military Jeep (at origin area, facing +Y direction) ---
jeep_x, jeep_y, jeep_z = 0.0, 0.0, 0.0

# Jeep body — main chassis
add_mesh("Jeep_Chassis", bpy.ops.mesh.primitive_cube_add, jeep_body_mat,
         (jeep_x, jeep_y, jeep_z + 0.65), (1.0, 1.8, 0.35))

# Jeep hood — front sloped section
add_mesh("Jeep_Hood", bpy.ops.mesh.primitive_cube_add, jeep_body_mat,
         (jeep_x, jeep_y + 1.6, jeep_z + 0.55), (0.85, 0.6, 0.2),
         rot=(math.radians(-10), 0, 0))

# Jeep rear cargo bed — open flat bed where gorilla stands
add_mesh("Jeep_CargoBed", bpy.ops.mesh.primitive_cube_add, jeep_frame_mat,
         (jeep_x, jeep_y - 1.2, jeep_z + 0.5), (0.95, 0.8, 0.05))

# Jeep rear side walls (low)
add_mesh("Jeep_SideL", bpy.ops.mesh.primitive_cube_add, jeep_body_mat,
         (jeep_x - 0.9, jeep_y - 1.2, jeep_z + 0.7), (0.05, 0.8, 0.2))
add_mesh("Jeep_SideR", bpy.ops.mesh.primitive_cube_add, jeep_body_mat,
         (jeep_x + 0.9, jeep_y - 1.2, jeep_z + 0.7), (0.05, 0.8, 0.2))

# Jeep rear gate
add_mesh("Jeep_RearGate", bpy.ops.mesh.primitive_cube_add, jeep_body_mat,
         (jeep_x, jeep_y - 2.0, jeep_z + 0.7), (0.9, 0.05, 0.2))

# Jeep windshield frame
add_mesh("Jeep_Windshield", bpy.ops.mesh.primitive_cube_add, jeep_frame_mat,
         (jeep_x, jeep_y + 0.9, jeep_z + 1.2), (0.9, 0.05, 0.4))

# Jeep roll bar
add_mesh("Jeep_RollBar", bpy.ops.mesh.primitive_cube_add, jeep_frame_mat,
         (jeep_x, jeep_y - 0.3, jeep_z + 1.3), (0.85, 0.04, 0.04))
add_mesh("Jeep_RollBarL", bpy.ops.mesh.primitive_cylinder_add, jeep_frame_mat,
         (jeep_x - 0.85, jeep_y - 0.3, jeep_z + 1.0), (0.04, 0.04, 0.35))
add_mesh("Jeep_RollBarR", bpy.ops.mesh.primitive_cylinder_add, jeep_frame_mat,
         (jeep_x + 0.85, jeep_y - 0.3, jeep_z + 1.0), (0.04, 0.04, 0.35))

# Wheels
for wx, wy, wname in [(-1.0, 1.0, "FL"), (1.0, 1.0, "FR"),
                       (-1.0, -1.0, "RL"), (1.0, -1.0, "RR")]:
    add_mesh(f"Jeep_Wheel_{wname}", bpy.ops.mesh.primitive_cylinder_add, jeep_wheel_mat,
             (jeep_x + wx, jeep_y + wy, jeep_z + 0.25), (0.3, 0.3, 0.12),
             rot=(0, math.radians(90), 0))

# --- Gorilla — standing in rear cargo bed, arms raised holding bat ---
build_large_figure("Gorilla", gorilla_mat, (jeep_x, jeep_y - 1.2, jeep_z + 0.55), pose="arms_raised")

# Baseball bat — held above gorilla's head
add_mesh("Bat_Handle", bpy.ops.mesh.primitive_cylinder_add, bat_mat,
         (jeep_x, jeep_y - 1.2, jeep_z + 3.3), (0.06, 0.06, 0.7),
         rot=(0, math.radians(15), math.radians(10)))
add_mesh("Bat_Barrel", bpy.ops.mesh.primitive_cylinder_add, bat_mat,
         (jeep_x + 0.25, jeep_y - 1.2, jeep_z + 3.9), (0.1, 0.1, 0.35),
         rot=(0, math.radians(15), math.radians(10)))

# --- Zombie — far ahead on right shoulder of road, walking/shambling ---
build_regular_male("Zombie", zombie_mat, (3.0, 14.0, 0.0), pose="standing")

# --- Camera — behind and above the jeep, looking forward down the road ---
setup_camera(scene, loc=(0.0, -6.0, 4.0), target_loc=(0.0, 5.0, 1.0), lens=24)

# Render
scene.frame_set(1)
scene.render.filepath = "/Users/jmordetsky/directors-chair/assets/generated/videos/zombie_mailbox_v2/layouts/layout_000.png"
bpy.ops.render.render(write_still=True)
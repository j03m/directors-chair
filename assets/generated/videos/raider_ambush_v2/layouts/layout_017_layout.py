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


# ── Scene Setup ──────────────────────────────────────────────────────────────

clean_scene()
scene = bpy.context.scene
setup_render(scene)
add_light(scene)

# ── Materials ────────────────────────────────────────────────────────────────

ground_mat = make_mat("Ground", (0.2, 0.15, 0.1, 1))
road_mat = make_mat("Road", (0.25, 0.22, 0.18, 1))
rifle_metal_mat = make_mat("RifleMetal", (0.12, 0.12, 0.13, 1))
rifle_wood_mat = make_mat("RifleWood", (0.3, 0.18, 0.08, 1))
truck_mat = make_mat("Truck", (0.35, 0.28, 0.2, 1))
tire_mat = make_mat("Tire", (0.08, 0.08, 0.08, 1))
cranial_mat = make_mat("Cranial", (0.25, 0.18, 0.1, 1))

# ── Ground ───────────────────────────────────────────────────────────────────

add_ground(ground_mat, size=15)

# Desert road surface strip
add_mesh("Road", bpy.ops.mesh.primitive_cube_add, road_mat,
         (0, 0, 0.005), (2.0, 15.0, 0.005))

# Scattered ground debris near the rifle for detail
add_mesh("Debris1", bpy.ops.mesh.primitive_cube_add, ground_mat,
         (0.3, -0.2, 0.01), (0.06, 0.04, 0.01),
         rot=(0, 0, math.radians(35)))
add_mesh("Debris2", bpy.ops.mesh.primitive_cube_add, ground_mat,
         (-0.15, 0.1, 0.01), (0.04, 0.03, 0.008),
         rot=(0, 0, math.radians(-20)))
add_mesh("Debris3", bpy.ops.mesh.primitive_cube_add, ground_mat,
         (0.12, 0.25, 0.008), (0.05, 0.025, 0.008),
         rot=(0, 0, math.radians(55)))

# ── Rifle (center of frame, lying on ground) ────────────────────────────────

# Barrel — long thin cylinder lying flat
add_mesh("Rifle_Barrel", bpy.ops.mesh.primitive_cylinder_add, rifle_metal_mat,
         (0.0, 0.15, 0.04), (0.018, 0.018, 0.45),
         rot=(math.radians(90), 0, math.radians(8)))

# Receiver/action body
add_mesh("Rifle_Receiver", bpy.ops.mesh.primitive_cube_add, rifle_metal_mat,
         (0.0, -0.18, 0.04), (0.03, 0.12, 0.04),
         rot=(0, 0, math.radians(8)))

# Stock — wooden
add_mesh("Rifle_Stock", bpy.ops.mesh.primitive_cube_add, rifle_wood_mat,
         (0.02, -0.45, 0.035), (0.025, 0.15, 0.05),
         rot=(0, 0, math.radians(8)))

# Magazine
add_mesh("Rifle_Mag", bpy.ops.mesh.primitive_cube_add, rifle_metal_mat,
         (-0.01, -0.1, 0.06), (0.015, 0.04, 0.035),
         rot=(0, math.radians(5), math.radians(8)))

# Scope mount
add_mesh("Rifle_Scope", bpy.ops.mesh.primitive_cylinder_add, rifle_metal_mat,
         (0.0, -0.05, 0.075), (0.012, 0.012, 0.08),
         rot=(math.radians(90), 0, math.radians(8)))

# ── Truck (background, blurred) ─────────────────────────────────────────────

truck_x, truck_y = 1.2, 5.5

# Truck cab
add_mesh("Truck_Cab", bpy.ops.mesh.primitive_cube_add, truck_mat,
         (truck_x, truck_y, 1.0), (0.8, 0.7, 0.7))

# Truck bed
add_mesh("Truck_Bed", bpy.ops.mesh.primitive_cube_add, truck_mat,
         (truck_x, truck_y + 1.5, 0.7), (0.85, 1.2, 0.45))

# Truck wheels
add_mesh("Truck_WheelFL", bpy.ops.mesh.primitive_cylinder_add, tire_mat,
         (truck_x - 0.85, truck_y - 0.3, 0.25), (0.25, 0.25, 0.1),
         rot=(0, math.radians(90), 0))
add_mesh("Truck_WheelFR", bpy.ops.mesh.primitive_cylinder_add, tire_mat,
         (truck_x + 0.85, truck_y - 0.3, 0.25), (0.25, 0.25, 0.1),
         rot=(0, math.radians(90), 0))
add_mesh("Truck_WheelRL", bpy.ops.mesh.primitive_cylinder_add, tire_mat,
         (truck_x - 0.85, truck_y + 2.0, 0.25), (0.25, 0.25, 0.1),
         rot=(0, math.radians(90), 0))
add_mesh("Truck_WheelRR", bpy.ops.mesh.primitive_cylinder_add, tire_mat,
         (truck_x + 0.85, truck_y + 2.0, 0.25), (0.25, 0.25, 0.1),
         rot=(0, math.radians(90), 0))

# ── Fallen Figure (background near truck) ───────────────────────────────────

build_regular_male("Cranial", cranial_mat, (-0.8, 4.5, 0), pose="fallen")

# ── Camera (low angle, close to ground, detail shot on rifle) ────────────────

camera = setup_camera(scene,
                      loc=(0.1, -1.2, 0.15),
                      target_loc=(0.0, 0.0, 0.04),
                      lens=35)

# Enable depth of field to blur the background
camera.data.dof.use_dof = True
camera.data.dof.focus_distance = 1.2
camera.data.dof.aperture_fstop = 1.4

# ── Render ───────────────────────────────────────────────────────────────────

scene.frame_set(1)
scene.render.filepath = "/Users/jmordetsky/directors-chair/assets/generated/videos/raider_ambush_v2/layouts/layout_017.png"
bpy.ops.render.render(write_still=True)
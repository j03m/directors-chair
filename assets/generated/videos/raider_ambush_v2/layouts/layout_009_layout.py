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

# Materials
ground_mat = make_mat("Ground", (0.2, 0.15, 0.1, 1))
cranial_mat = make_mat("Cranial", (0.25, 0.18, 0.1, 1))
muzzle_flash_mat = make_mat("MuzzleFlash", (1.0, 0.85, 0.2, 1))
rifle_mat = make_mat("Rifle", (0.12, 0.1, 0.08, 1))
dust_mat = make_mat("Dust", (0.6, 0.5, 0.35, 1))
cliff_mat = make_mat("Cliff", (0.35, 0.25, 0.15, 1))
desert_mat = make_mat("Desert", (0.55, 0.42, 0.28, 1))

# Ground plane (desert floor far below)
add_ground(ground_mat, size=20)

# ── Cliff Edge ───────────────────────────────────────────────────────────────
# Raised platform representing the cliff top where the figure is prone
add_mesh("CliffTop", bpy.ops.mesh.primitive_cube_add, cliff_mat,
         (0, 0, 1.0), (4, 6, 1.0))

# Cliff face dropping away in front
add_mesh("CliffFace", bpy.ops.mesh.primitive_cube_add, cliff_mat,
         (0, -6, -1.5), (4, 1.5, 3.5))

# Desert landscape below and beyond
add_mesh("DesertFloor", bpy.ops.mesh.primitive_plane_add, desert_mat,
         (0, -15, -4.0), (12, 10, 1))

# Distant mesa/butte shapes for depth
add_mesh("Mesa1", bpy.ops.mesh.primitive_cube_add, cliff_mat,
         (-8, -25, -2.0), (2.5, 1.5, 3.0))
add_mesh("Mesa2", bpy.ops.mesh.primitive_cube_add, cliff_mat,
         (6, -30, -2.5), (3.0, 1.0, 2.5))

# ── Prone Figure (Cranial) ──────────────────────────────────────────────────
# Prone/fallen pose at cliff edge, facing forward (negative Y), arms extended
# Using "fallen" pose but repositioned to be belly-down at cliff edge
# Body prone on cliff top, head facing out over the edge
add_mesh("Cranial_Body", bpy.ops.mesh.primitive_cube_add, cranial_mat,
         (0, -1.5, 2.3), (0.45, 0.3, 0.7),
         rot=(math.radians(85), 0, 0))
add_mesh("Cranial_Head", bpy.ops.mesh.primitive_cube_add, cranial_mat,
         (0, -2.5, 2.25), (0.2, 0.18, 0.2),
         rot=(math.radians(80), 0, 0))

# Arms extended forward holding rifle
add_mesh("Cranial_ArmL", bpy.ops.mesh.primitive_cylinder_add, cranial_mat,
         (-0.25, -2.8, 2.2), (0.1, 0.1, 0.5),
         rot=(math.radians(90), 0, math.radians(5)))
add_mesh("Cranial_ArmR", bpy.ops.mesh.primitive_cylinder_add, cranial_mat,
         (0.25, -2.8, 2.2), (0.1, 0.1, 0.5),
         rot=(math.radians(90), 0, math.radians(-5)))

# Legs trailing behind
add_mesh("Cranial_LegL", bpy.ops.mesh.primitive_cylinder_add, cranial_mat,
         (-0.25, -0.2, 2.15), (0.1, 0.1, 0.5),
         rot=(math.radians(88), 0, math.radians(-8)))
add_mesh("Cranial_LegR", bpy.ops.mesh.primitive_cylinder_add, cranial_mat,
         (0.25, -0.3, 2.15), (0.1, 0.1, 0.5),
         rot=(math.radians(88), 0, math.radians(8)))

# ── Rifle ────────────────────────────────────────────────────────────────────
add_mesh("Rifle", bpy.ops.mesh.primitive_cylinder_add, rifle_mat,
         (0, -3.8, 2.2), (0.04, 0.04, 1.2),
         rot=(math.radians(90), 0, 0))

# Rifle stock (thicker section near body)
add_mesh("RifleStock", bpy.ops.mesh.primitive_cube_add, rifle_mat,
         (0, -2.3, 2.22), (0.06, 0.2, 0.04))

# ── Muzzle Flash ─────────────────────────────────────────────────────────────
# Bright burst at the end of the rifle barrel
muzzle_flash_mat.use_nodes = True
bsdf = muzzle_flash_mat.node_tree.nodes["Principled BSDF"]
bsdf.inputs["Emission Color"].default_value = (1.0, 0.7, 0.1, 1)
bsdf.inputs["Emission Strength"].default_value = 15.0

add_mesh("MuzzleFlash1", bpy.ops.mesh.primitive_uv_sphere_add, muzzle_flash_mat,
         (0, -5.0, 2.2), (0.15, 0.3, 0.15))
add_mesh("MuzzleFlash2", bpy.ops.mesh.primitive_uv_sphere_add, muzzle_flash_mat,
         (0.08, -5.2, 2.3), (0.08, 0.15, 0.08))
add_mesh("MuzzleFlash3", bpy.ops.mesh.primitive_uv_sphere_add, muzzle_flash_mat,
         (-0.06, -5.15, 2.1), (0.06, 0.12, 0.06))

# Point light for muzzle flash illumination
bpy.ops.object.light_add(type='POINT', location=(0, -5.0, 2.3))
flash_light = bpy.context.active_object
flash_light.name = "MuzzleLight"
flash_light.data.energy = 500
flash_light.data.color = (1.0, 0.7, 0.2)

# ── Dust Kicks ───────────────────────────────────────────────────────────────
# Dust clouds near the muzzle and cliff edge from the blast
add_mesh("Dust1", bpy.ops.mesh.primitive_uv_sphere_add, dust_mat,
         (0.3, -4.5, 2.0), (0.2, 0.15, 0.12))
add_mesh("Dust2", bpy.ops.mesh.primitive_uv_sphere_add, dust_mat,
         (-0.2, -4.8, 1.9), (0.15, 0.2, 0.1))
add_mesh("Dust3", bpy.ops.mesh.primitive_uv_sphere_add, dust_mat,
         (0.1, -3.5, 2.05), (0.25, 0.18, 0.15))

# ── Camera: Over the Shoulder ────────────────────────────────────────────────
# Behind and slightly above the prone figure, looking past the shoulder
# toward the muzzle flash and desert beyond
setup_camera(scene,
             loc=(0.8, 1.5, 3.5),
             target_loc=(0, -5.0, 1.5),
             lens=24)

# ── Render ───────────────────────────────────────────────────────────────────
scene.frame_set(1)
scene.render.filepath = "/Users/jmordetsky/directors-chair/assets/generated/videos/raider_ambush_v2/layouts/layout_009.png"
bpy.ops.render.render(write_still=True)
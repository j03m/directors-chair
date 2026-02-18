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


# === SCENE SETUP ===

clean_scene()
scene = bpy.context.scene
setup_render(scene)
add_light(scene)

# Materials
mat_ground = make_mat("Ground", (0.2, 0.15, 0.1, 1))
mat_heavy = make_mat("Heavy", (0.25, 0.18, 0.1, 1))
mat_truck = make_mat("Truck", (0.3, 0.25, 0.2, 1))
mat_axe = make_mat("Axe", (0.4, 0.4, 0.4, 1))
mat_dust = make_mat("Dust", (0.6, 0.5, 0.35, 0.6))

# Ground
add_ground(mat_ground, size=15)

# Heavy raider — knocked backwards, airborne, arms flung wide
# Using a custom airborne pose since "fallen" is on the ground
# Place him center-frame, elevated off ground to show airborne
x_h, y_h, z_h = 0, 0, 0

# Body tilted backwards and slightly airborne
add_mesh("Heavy_Body", bpy.ops.mesh.primitive_cube_add, mat_heavy,
         (x_h, y_h, z_h + 1.2), (0.65, 0.45, 0.75),
         rot=(math.radians(-35), 0, math.radians(5)))

# Head snapping back
add_mesh("Heavy_Head", bpy.ops.mesh.primitive_uv_sphere_add, mat_heavy,
         (x_h + 0.2, y_h, z_h + 2.1), (0.38, 0.33, 0.33),
         rot=(math.radians(-25), 0, 0))

# Arms flung wide outward
add_mesh("Heavy_ArmL", bpy.ops.mesh.primitive_cylinder_add, mat_heavy,
         (x_h - 1.1, y_h + 0.2, z_h + 1.5), (0.14, 0.14, 0.55),
         rot=(math.radians(-20), math.radians(15), math.radians(-70)))
add_mesh("Heavy_ArmR", bpy.ops.mesh.primitive_cylinder_add, mat_heavy,
         (x_h + 1.2, y_h - 0.3, z_h + 1.7), (0.14, 0.14, 0.55),
         rot=(math.radians(10), math.radians(-20), math.radians(65)))

# Legs kicking up from the impact
add_mesh("Heavy_LegL", bpy.ops.mesh.primitive_cylinder_add, mat_heavy,
         (x_h - 0.4, y_h + 0.3, z_h + 0.3), (0.16, 0.16, 0.45),
         rot=(math.radians(30), 0, math.radians(-10)))
add_mesh("Heavy_LegR", bpy.ops.mesh.primitive_cylinder_add, mat_heavy,
         (x_h + 0.5, y_h + 0.4, z_h + 0.2), (0.16, 0.16, 0.45),
         rot=(math.radians(40), 0, math.radians(15)))

# Axe flying away from his hand (upper right)
add_mesh("Axe_Handle", bpy.ops.mesh.primitive_cylinder_add, mat_axe,
         (x_h + 2.0, y_h - 0.5, z_h + 2.3), (0.04, 0.04, 0.4),
         rot=(math.radians(25), math.radians(-40), math.radians(55)))
add_mesh("Axe_Blade", bpy.ops.mesh.primitive_cube_add, mat_axe,
         (x_h + 2.2, y_h - 0.7, z_h + 2.7), (0.15, 0.03, 0.12),
         rot=(math.radians(25), math.radians(-40), math.radians(55)))

# Truck behind him — simple box shape
add_mesh("Truck_Body", bpy.ops.mesh.primitive_cube_add, mat_truck,
         (x_h, y_h + 3.5, z_h + 1.2), (1.2, 2.0, 1.0))
add_mesh("Truck_Cab", bpy.ops.mesh.primitive_cube_add, mat_truck,
         (x_h, y_h + 5.8, z_h + 1.5), (1.0, 0.8, 0.7))
# Wheels
mat_wheel = make_mat("Wheel", (0.1, 0.1, 0.1, 1))
add_mesh("Truck_WheelFL", bpy.ops.mesh.primitive_cylinder_add, mat_wheel,
         (x_h - 1.3, y_h + 5.0, z_h + 0.3), (0.3, 0.3, 0.15),
         rot=(math.radians(90), 0, 0))
add_mesh("Truck_WheelFR", bpy.ops.mesh.primitive_cylinder_add, mat_wheel,
         (x_h + 1.3, y_h + 5.0, z_h + 0.3), (0.3, 0.3, 0.15),
         rot=(math.radians(90), 0, 0))
add_mesh("Truck_WheelRL", bpy.ops.mesh.primitive_cylinder_add, mat_wheel,
         (x_h - 1.3, y_h + 2.5, z_h + 0.3), (0.3, 0.3, 0.15),
         rot=(math.radians(90), 0, 0))
add_mesh("Truck_WheelRR", bpy.ops.mesh.primitive_cylinder_add, mat_wheel,
         (x_h + 1.3, y_h + 2.5, z_h + 0.3), (0.3, 0.3, 0.15),
         rot=(math.radians(90), 0, 0))

# Dust and debris — scattered small cubes/spheres near ground
for i in range(8):
    angle = i * math.radians(45)
    dx = math.cos(angle) * (1.0 + i * 0.15)
    dy = math.sin(angle) * (0.8 + i * 0.1)
    dz = 0.1 + (i % 3) * 0.15
    add_mesh(f"Dust_{i}", bpy.ops.mesh.primitive_uv_sphere_add, mat_dust,
             (x_h + dx, y_h + dy, z_h + dz), (0.08 + i * 0.02, 0.08 + i * 0.02, 0.06))

# Camera — medium shot from front-left, capturing the airborne heavy and truck behind
setup_camera(scene, loc=(4.0, -5.0, 2.5), target_loc=(0, 0, 1.3), lens=32)

# Render
scene.frame_set(1)
scene.render.filepath = "/Users/jmordetsky/directors-chair/assets/generated/videos/raider_ambush_v2/layouts/layout_024.png"
bpy.ops.render.render(write_still=True)
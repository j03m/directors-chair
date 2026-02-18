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


# ============================================================
# SCENE SETUP
# ============================================================

clean_scene()
scene = bpy.context.scene
setup_render(scene)
add_light(scene)

# Materials
mat_ground = make_mat("Ground", (0.2, 0.15, 0.1, 1))
mat_road = make_mat("Road", (0.12, 0.1, 0.08, 1))
mat_motorcycle = make_mat("Motorcycle", (0.15, 0.15, 0.18, 1))
mat_chrome = make_mat("Chrome", (0.5, 0.5, 0.55, 1))
mat_debris_dark = make_mat("DebrisDark", (0.18, 0.12, 0.08, 1))
mat_debris_rust = make_mat("DebrisRust", (0.4, 0.2, 0.1, 1))
mat_debris_wood = make_mat("DebrisWood", (0.3, 0.2, 0.1, 1))
mat_scope_ring = make_mat("ScopeRing", (0.02, 0.02, 0.02, 1))
mat_tire = make_mat("Tire", (0.05, 0.05, 0.05, 1))

# Ground
add_ground(mat_ground, size=20)

# Desert road — long flat strip
add_mesh("Road", bpy.ops.mesh.primitive_cube_add, mat_road,
         (0, 0, 0.01), (1.5, 12, 0.02))

# Road edge lines (faded paint)
mat_paint = make_mat("Paint", (0.35, 0.3, 0.2, 1))
add_mesh("RoadLineL", bpy.ops.mesh.primitive_cube_add, mat_paint,
         (-1.4, 0, 0.02), (0.03, 12, 0.01))
add_mesh("RoadLineR", bpy.ops.mesh.primitive_cube_add, mat_paint,
         (1.4, 0, 0.02), (0.03, 12, 0.01))

# ============================================================
# ROADBLOCK — motorcycle + debris at far end of road
# ============================================================

# Motorcycle body (laid on its side)
add_mesh("MotoBody", bpy.ops.mesh.primitive_cube_add, mat_motorcycle,
         (0.3, 6, 0.35), (0.25, 0.7, 0.2),
         rot=(0, 0, math.radians(15)))

# Motorcycle wheels
add_mesh("MotoWheelF", bpy.ops.mesh.primitive_torus_add, mat_tire,
         (0.2, 6.7, 0.3), (0.3, 0.3, 0.3),
         rot=(math.radians(90), 0, math.radians(15)))
add_mesh("MotoWheelR", bpy.ops.mesh.primitive_torus_add, mat_tire,
         (0.4, 5.3, 0.3), (0.3, 0.3, 0.3),
         rot=(math.radians(90), 0, math.radians(15)))

# Motorcycle handlebars
add_mesh("MotoHandlebar", bpy.ops.mesh.primitive_cylinder_add, mat_chrome,
         (0.15, 6.9, 0.55), (0.03, 0.03, 0.3),
         rot=(math.radians(20), math.radians(70), 0))

# Motorcycle exhaust pipe
add_mesh("MotoExhaust", bpy.ops.mesh.primitive_cylinder_add, mat_chrome,
         (0.5, 5.8, 0.15), (0.04, 0.04, 0.5),
         rot=(math.radians(90), 0, math.radians(15)))

# Debris — scattered barrels, crates, metal sheets around the motorcycle
add_mesh("Barrel1", bpy.ops.mesh.primitive_cylinder_add, mat_debris_rust,
         (-0.8, 5.5, 0.4), (0.25, 0.25, 0.4),
         rot=(math.radians(8), 0, 0))
add_mesh("Barrel2", bpy.ops.mesh.primitive_cylinder_add, mat_debris_rust,
         (1.2, 6.5, 0.35), (0.22, 0.22, 0.35),
         rot=(math.radians(-5), math.radians(10), 0))
add_mesh("Barrel3_Fallen", bpy.ops.mesh.primitive_cylinder_add, mat_debris_dark,
         (-0.3, 7.2, 0.2), (0.22, 0.22, 0.35),
         rot=(math.radians(85), 0, math.radians(30)))

# Crates
add_mesh("Crate1", bpy.ops.mesh.primitive_cube_add, mat_debris_wood,
         (-1.3, 6.8, 0.3), (0.3, 0.3, 0.3),
         rot=(0, 0, math.radians(20)))
add_mesh("Crate2", bpy.ops.mesh.primitive_cube_add, mat_debris_wood,
         (0.9, 7.5, 0.25), (0.25, 0.25, 0.25),
         rot=(0, 0, math.radians(-10)))

# Sheet metal debris
add_mesh("MetalSheet1", bpy.ops.mesh.primitive_cube_add, mat_debris_dark,
         (-0.5, 6.2, 0.05), (0.5, 0.3, 0.015),
         rot=(0, 0, math.radians(25)))
add_mesh("MetalSheet2", bpy.ops.mesh.primitive_cube_add, mat_chrome,
         (1.5, 5.8, 0.08), (0.35, 0.2, 0.01),
         rot=(math.radians(5), 0, math.radians(-15)))

# Scattered tire
add_mesh("LooseTire", bpy.ops.mesh.primitive_torus_add, mat_tire,
         (-1.6, 7.0, 0.2), (0.25, 0.25, 0.25),
         rot=(math.radians(70), math.radians(15), 0))

# Small rocks / rubble
add_mesh("Rock1", bpy.ops.mesh.primitive_uv_sphere_add, mat_ground,
         (0.6, 5.0, 0.08), (0.1, 0.12, 0.07))
add_mesh("Rock2", bpy.ops.mesh.primitive_uv_sphere_add, mat_ground,
         (-0.9, 6.0, 0.06), (0.08, 0.1, 0.06))
add_mesh("Rock3", bpy.ops.mesh.primitive_uv_sphere_add, mat_ground,
         (1.0, 7.8, 0.07), (0.12, 0.09, 0.06))

# ============================================================
# SNIPER SCOPE VIGNETTE — black ring framing the view
# ============================================================

# Outer ring (thick black torus very close to camera to frame the shot)
add_mesh("ScopeRing", bpy.ops.mesh.primitive_torus_add, mat_scope_ring,
         (0, -7.8, 1.5), (1.8, 1.8, 1.8),
         rot=(math.radians(90), 0, 0))

# Crosshair lines (thin cylinders crossing through scope center)
mat_crosshair = make_mat("Crosshair", (0.02, 0.02, 0.02, 1))
add_mesh("CrosshairH", bpy.ops.mesh.primitive_cylinder_add, mat_crosshair,
         (0, -7.8, 1.5), (0.005, 0.005, 1.6),
         rot=(0, math.radians(90), 0))
add_mesh("CrosshairV", bpy.ops.mesh.primitive_cylinder_add, mat_crosshair,
         (0, -7.8, 1.5), (0.005, 0.005, 1.6),
         rot=(0, 0, 0))

# Scope body blocks (top/bottom/left/right to mask outside the circle)
mat_scope_body = make_mat("ScopeBody", (0.01, 0.01, 0.01, 1))
add_mesh("ScopeMaskTop", bpy.ops.mesh.primitive_cube_add, mat_scope_body,
         (0, -7.75, 3.8), (3, 0.3, 1.5))
add_mesh("ScopeMaskBot", bpy.ops.mesh.primitive_cube_add, mat_scope_body,
         (0, -7.75, -0.8), (3, 0.3, 1.5))
add_mesh("ScopeMaskL", bpy.ops.mesh.primitive_cube_add, mat_scope_body,
         (-3.2, -7.75, 1.5), (1.5, 0.3, 3))
add_mesh("ScopeMaskR", bpy.ops.mesh.primitive_cube_add, mat_scope_body,
         (3.2, -7.75, 1.5), (1.5, 0.3, 3))

# ============================================================
# CAMERA — looking down the road toward the roadblock
# ============================================================

setup_camera(scene, loc=(0, -8, 1.5), target_loc=(0, 6.5, 0.3), lens=35)

# ============================================================
# RENDER
# ============================================================

scene.frame_set(1)
scene.render.filepath = "/Users/jmordetsky/directors-chair/assets/generated/videos/raider_ambush_v2/layouts/layout_001.png"
bpy.ops.render.render(write_still=True)
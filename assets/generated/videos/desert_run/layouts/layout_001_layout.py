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

mat_ground = make_mat("Ground", (0.2, 0.15, 0.1, 1))
mat_cranial = make_mat("Cranial", (0.25, 0.18, 0.1, 1))
mat_robot = make_mat("Robot", (0.6, 0.6, 0.65, 1))
mat_gorilla = make_mat("Gorilla", (0.2, 0.35, 0.5, 1))
mat_jeep_body = make_mat("JeepBody", (0.22, 0.24, 0.18, 1))
mat_jeep_dark = make_mat("JeepDark", (0.08, 0.08, 0.08, 1))
mat_windshield = make_mat("Windshield", (0.5, 0.6, 0.7, 0.3))
mat_tire = make_mat("Tire", (0.05, 0.05, 0.05, 1))
mat_rollbar = make_mat("RollBar", (0.12, 0.12, 0.12, 1))
mat_grille = make_mat("Grille", (0.15, 0.15, 0.15, 1))
mat_headlight = make_mat("Headlight", (1.0, 0.95, 0.7, 1))

# Make headlight emissive
hl_bsdf = mat_headlight.node_tree.nodes["Principled BSDF"]
hl_bsdf.inputs["Emission Color"].default_value = (1.0, 0.95, 0.7, 1)
hl_bsdf.inputs["Emission Strength"].default_value = 5.0

# ── Ground ───────────────────────────────────────────────────────────────────

add_ground(mat_ground, size=20)

# ── Desert Road ──────────────────────────────────────────────────────────────

mat_road = make_mat("Road", (0.18, 0.16, 0.12, 1))
add_mesh("Road", bpy.ops.mesh.primitive_cube_add, mat_road,
         (0, 0, 0.01), (3.0, 20.0, 0.01))

# ── Jeep Construction ───────────────────────────────────────────────────────
# Jeep positioned at center, oriented along Y axis (driving toward -Y / camera)
# Jeep center at (0, 0, 0.5)

jeep_x, jeep_y, jeep_z = 0.0, 0.0, 0.0

# Main body / chassis
add_mesh("Jeep_Chassis", bpy.ops.mesh.primitive_cube_add, mat_jeep_body,
         (jeep_x, jeep_y, jeep_z + 0.55), (1.0, 2.0, 0.25))

# Hood (front section, lower)
add_mesh("Jeep_Hood", bpy.ops.mesh.primitive_cube_add, mat_jeep_body,
         (jeep_x, jeep_y - 1.6, jeep_z + 0.55), (0.9, 0.7, 0.15))

# Front grille face
add_mesh("Jeep_Grille", bpy.ops.mesh.primitive_cube_add, mat_grille,
         (jeep_x, jeep_y - 2.3, jeep_z + 0.55), (0.85, 0.05, 0.22))

# Headlights
add_mesh("Jeep_HeadlightL", bpy.ops.mesh.primitive_uv_sphere_add, mat_headlight,
         (jeep_x - 0.55, jeep_y - 2.35, jeep_z + 0.6), (0.1, 0.05, 0.1))
add_mesh("Jeep_HeadlightR", bpy.ops.mesh.primitive_uv_sphere_add, mat_headlight,
         (jeep_x + 0.55, jeep_y - 2.35, jeep_z + 0.6), (0.1, 0.05, 0.1))

# Cabin sides (open top, just the lower walls)
add_mesh("Jeep_SideL", bpy.ops.mesh.primitive_cube_add, mat_jeep_body,
         (jeep_x - 0.95, jeep_y + 0.2, jeep_z + 0.85), (0.08, 1.5, 0.2))
add_mesh("Jeep_SideR", bpy.ops.mesh.primitive_cube_add, mat_jeep_body,
         (jeep_x + 0.95, jeep_y + 0.2, jeep_z + 0.85), (0.08, 1.5, 0.2))

# Rear panel
add_mesh("Jeep_Rear", bpy.ops.mesh.primitive_cube_add, mat_jeep_body,
         (jeep_x, jeep_y + 1.7, jeep_z + 0.85), (0.95, 0.08, 0.25))

# Windshield frame (flat, angled slightly back)
add_mesh("Jeep_Windshield", bpy.ops.mesh.primitive_cube_add, mat_windshield,
         (jeep_x, jeep_y - 0.85, jeep_z + 1.2), (0.88, 0.04, 0.35),
         rot=(math.radians(-15), 0, 0))

# Roll bars - two vertical posts behind seats
add_mesh("Jeep_RollBarL", bpy.ops.mesh.primitive_cylinder_add, mat_rollbar,
         (jeep_x - 0.85, jeep_y + 0.6, jeep_z + 1.35), (0.04, 0.04, 0.45))
add_mesh("Jeep_RollBarR", bpy.ops.mesh.primitive_cylinder_add, mat_rollbar,
         (jeep_x + 0.85, jeep_y + 0.6, jeep_z + 1.35), (0.04, 0.04, 0.45))

# Roll bar cross beam
add_mesh("Jeep_RollBarTop", bpy.ops.mesh.primitive_cylinder_add, mat_rollbar,
         (jeep_x, jeep_y + 0.6, jeep_z + 1.8), (0.035, 0.035, 0.85),
         rot=(0, math.radians(90), 0))

# Seats - driver (left) and passenger (right)
mat_seat = make_mat("Seat", (0.1, 0.08, 0.06, 1))
add_mesh("Jeep_SeatL", bpy.ops.mesh.primitive_cube_add, mat_seat,
         (jeep_x - 0.45, jeep_y - 0.1, jeep_z + 0.85), (0.3, 0.35, 0.1))
add_mesh("Jeep_SeatBackL", bpy.ops.mesh.primitive_cube_add, mat_seat,
         (jeep_x - 0.45, jeep_y + 0.2, jeep_z + 1.1), (0.3, 0.06, 0.2))
add_mesh("Jeep_SeatR", bpy.ops.mesh.primitive_cube_add, mat_seat,
         (jeep_x + 0.45, jeep_y - 0.1, jeep_z + 0.85), (0.3, 0.35, 0.1))
add_mesh("Jeep_SeatBackR", bpy.ops.mesh.primitive_cube_add, mat_seat,
         (jeep_x + 0.45, jeep_y + 0.2, jeep_z + 1.1), (0.3, 0.06, 0.2))

# Steering wheel (left side / driver)
add_mesh("Jeep_SteeringCol", bpy.ops.mesh.primitive_cylinder_add, mat_jeep_dark,
         (jeep_x - 0.45, jeep_y - 0.55, jeep_z + 1.1), (0.02, 0.02, 0.25),
         rot=(math.radians(-30), 0, 0))
add_mesh("Jeep_SteeringWheel", bpy.ops.mesh.primitive_torus_add, mat_jeep_dark,
         (jeep_x - 0.45, jeep_y - 0.65, jeep_z + 1.25), (0.12, 0.12, 0.12),
         rot=(math.radians(60), 0, 0))

# Wheels / Tires - 4 wheels
wheel_positions = [
    (jeep_x - 1.05, jeep_y - 1.3, jeep_z + 0.25),  # Front left
    (jeep_x + 1.05, jeep_y - 1.3, jeep_z + 0.25),  # Front right
    (jeep_x - 1.05, jeep_y + 1.2, jeep_z + 0.25),   # Rear left
    (jeep_x + 1.05, jeep_y + 1.2, jeep_z + 0.25),   # Rear right
]
for i, wpos in enumerate(wheel_positions):
    add_mesh(f"Jeep_Tire_{i}", bpy.ops.mesh.primitive_cylinder_add, mat_tire,
             wpos, (0.25, 0.25, 0.12),
             rot=(0, math.radians(90), 0))

# Fender / wheel arches
add_mesh("Jeep_FenderFL", bpy.ops.mesh.primitive_cube_add, mat_jeep_body,
         (jeep_x - 1.0, jeep_y - 1.3, jeep_z + 0.45), (0.15, 0.4, 0.08))
add_mesh("Jeep_FenderFR", bpy.ops.mesh.primitive_cube_add, mat_jeep_body,
         (jeep_x + 1.0, jeep_y - 1.3, jeep_z + 0.45), (0.15, 0.4, 0.08))
add_mesh("Jeep_FenderRL", bpy.ops.mesh.primitive_cube_add, mat_jeep_body,
         (jeep_x - 1.0, jeep_y + 1.2, jeep_z + 0.45), (0.15, 0.4, 0.08))
add_mesh("Jeep_FenderRR", bpy.ops.mesh.primitive_cube_add, mat_jeep_body,
         (jeep_x + 1.0, jeep_y + 1.2, jeep_z + 0.45), (0.15, 0.4, 0.08))

# ── Characters in Jeep ──────────────────────────────────────────────────────

# Driver (cranial) - left seat, seated pose
build_regular_male("Cranial", mat_cranial, (jeep_x - 0.45, jeep_y - 0.1, jeep_z + 0.85), pose="seated")

# Passenger (robot) - right seat, seated pose
build_regular_male("Robot", mat_robot, (jeep_x + 0.45, jeep_y - 0.1, jeep_z + 0.85), pose="seated")

# Gorilla - rear cargo area, seated/hulking
build_large_figure("Gorilla", mat_gorilla, (jeep_x, jeep_y + 1.1, jeep_z + 0.55), pose="seated")

# ── Dust clouds for motion ──────────────────────────────────────────────────

mat_dust = make_mat("Dust", (0.35, 0.3, 0.22, 1))
dust_bsdf = mat_dust.node_tree.nodes["Principled BSDF"]
dust_bsdf.inputs["Alpha"].default_value = 0.3
mat_dust.blend_method = 'BLEND' if hasattr(mat_dust, 'blend_method') else None

add_mesh("Dust1", bpy.ops.mesh.primitive_uv_sphere_add, mat_dust,
         (0.5, 3.0, 0.2), (0.8, 0.6, 0.3))
add_mesh("Dust2", bpy.ops.mesh.primitive_uv_sphere_add, mat_dust,
         (-0.4, 3.5, 0.15), (1.0, 0.7, 0.25))
add_mesh("Dust3", bpy.ops.mesh.primitive_uv_sphere_add, mat_dust,
         (0.2, 4.0, 0.3), (1.2, 0.8, 0.35))

# ── Camera ───────────────────────────────────────────────────────────────────
# Three-quarter front tracking shot: camera ahead and to the left at 45 degrees,
# slightly below windshield level, looking back at the jeep

setup_camera(scene,
             loc=(-3.5, -4.5, 1.0),
             target_loc=(0.0, 0.0, 1.0),
             lens=35)

# ── Render ───────────────────────────────────────────────────────────────────

scene.frame_set(1)
scene.render.filepath = "/Users/jmordetsky/directors-chair/assets/generated/videos/desert_run/layouts/layout_001.png"
bpy.ops.render.render(write_still=True)
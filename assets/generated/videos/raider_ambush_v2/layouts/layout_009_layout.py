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


# ── Scene Setup ──────────────────────────────────────────────
clean_scene()
scene = bpy.context.scene
setup_render(scene)
add_light(scene)

# ── Materials ────────────────────────────────────────────────
mat_ground = make_mat("DesertFloor", (0.2, 0.15, 0.1, 1))
mat_cliff = make_mat("CliffRock", (0.28, 0.22, 0.14, 1))
mat_cliff_face = make_mat("CliffFace", (0.22, 0.17, 0.1, 1))
mat_road = make_mat("Road", (0.12, 0.1, 0.08, 1))
mat_road_stripe = make_mat("RoadStripe", (0.4, 0.35, 0.2, 1))
mat_truck_body = make_mat("TruckBody", (0.4, 0.32, 0.2, 1))
mat_truck_cab = make_mat("TruckCab", (0.35, 0.28, 0.18, 1))
mat_truck_wheels = make_mat("TruckWheels", (0.08, 0.08, 0.08, 1))

mat_heavy = make_mat("Heavy", (0.25, 0.18, 0.1, 1))
mat_nomad1 = make_mat("Nomad1", (0.3, 0.4, 0.2, 1))
mat_nomad2 = make_mat("Nomad2", (0.25, 0.18, 0.1, 1))
mat_nomad3 = make_mat("Nomad3", (0.6, 0.6, 0.65, 1))
mat_hockey = make_mat("Hockey", (0.2, 0.35, 0.5, 1))
mat_goggles = make_mat("Goggles", (0.5, 0.2, 0.2, 1))

# ── Ground (desert floor at z=0) ────────────────────────────
add_ground(mat_ground, size=40)

# ── Cliff (foreground, raised platform) ─────────────────────
# Main cliff top — top surface at z=10
add_mesh("CliffTop", bpy.ops.mesh.primitive_cube_add, mat_cliff,
         (0, 0, 5), (6, 5, 5))
# Cliff face — vertical wall facing the road
add_mesh("CliffFace", bpy.ops.mesh.primitive_cube_add, mat_cliff_face,
         (0, 6, 5), (5, 0.5, 5))
# Rubble at cliff base
add_mesh("Rubble1", bpy.ops.mesh.primitive_cube_add, mat_cliff_face,
         (-2, 7, 0.4), (1.2, 0.8, 0.4),
         rot=(0, 0, math.radians(15)))
add_mesh("Rubble2", bpy.ops.mesh.primitive_cube_add, mat_cliff_face,
         (1.5, 7.5, 0.3), (0.8, 0.6, 0.3),
         rot=(0, 0, math.radians(-10)))

# ── Road (far below, running along X axis) ──────────────────
add_mesh("Road", bpy.ops.mesh.primitive_cube_add, mat_road,
         (0, 22, 0.02), (15, 2, 0.02))
# Center stripe
add_mesh("Stripe1", bpy.ops.mesh.primitive_cube_add, mat_road_stripe,
         (-6, 22, 0.04), (1.5, 0.08, 0.01))
add_mesh("Stripe2", bpy.ops.mesh.primitive_cube_add, mat_road_stripe,
         (-2, 22, 0.04), (1.5, 0.08, 0.01))
add_mesh("Stripe3", bpy.ops.mesh.primitive_cube_add, mat_road_stripe,
         (2, 22, 0.04), (1.5, 0.08, 0.01))
add_mesh("Stripe4", bpy.ops.mesh.primitive_cube_add, mat_road_stripe,
         (6, 22, 0.04), (1.5, 0.08, 0.01))

# ── Cab-Over Truck (stopped on road, angled slightly) ───────
# Cargo bed (long box behind cab)
add_mesh("TruckBed", bpy.ops.mesh.primitive_cube_add, mat_truck_body,
         (1.5, 22, 1.2), (2.5, 1.2, 1.2),
         rot=(0, 0, math.radians(5)))
# Cab (flat-front, directly over front axle)
add_mesh("TruckCab", bpy.ops.mesh.primitive_cube_add, mat_truck_cab,
         (-1.8, 22.1, 1.3), (1.0, 1.1, 1.3),
         rot=(0, 0, math.radians(5)))
# Wheels
add_mesh("WheelFL", bpy.ops.mesh.primitive_cylinder_add, mat_truck_wheels,
         (-2.2, 20.8, 0.3), (0.3, 0.3, 0.15),
         rot=(math.radians(90), 0, 0))
add_mesh("WheelFR", bpy.ops.mesh.primitive_cylinder_add, mat_truck_wheels,
         (-2.2, 23.2, 0.3), (0.3, 0.3, 0.15),
         rot=(math.radians(90), 0, 0))
add_mesh("WheelRL", bpy.ops.mesh.primitive_cylinder_add, mat_truck_wheels,
         (2.8, 20.8, 0.3), (0.3, 0.3, 0.15),
         rot=(math.radians(90), 0, 0))
add_mesh("WheelRR", bpy.ops.mesh.primitive_cylinder_add, mat_truck_wheels,
         (2.8, 23.2, 0.3), (0.3, 0.3, 0.15),
         rot=(math.radians(90), 0, 0))

# ── Foreground: Heavy raider prone on cliff edge ────────────
# Lying face-down at cliff edge, peering over (body oriented toward +Y)
build_large_figure("Heavy", mat_heavy, (0.5, 4.2, 10), pose="fallen")

# ── Figures on road below (scattered around truck) ──────────
# Nomad1 — running away from truck toward road edge
build_regular_male("Nomad1", mat_nomad1, (-5, 21, 0.05), pose="standing")

# Nomad2 — ducking behind truck bed for cover
build_regular_male("Nomad2", mat_nomad2, (3, 23.5, 0.05), pose="fighting_stance")

# Nomad3 — crouching behind truck cab
build_regular_male("Nomad3", mat_nomad3, (-2.5, 23.8, 0.05), pose="fighting_stance")

# Hockey raider — advancing on road
build_regular_male("Hockey", mat_hockey, (-4, 23, 0.05), pose="standing")

# Goggles raider — on opposite side of truck
build_regular_male("Goggles", mat_goggles, (5, 21.5, 0.05), pose="standing")

# One figure collapsing on the road
build_regular_male("Fallen", mat_nomad1, (0, 20.5, 0.05), pose="fallen")

# ── Camera: over the shoulder of prone Heavy, looking down ──
setup_camera(scene,
             loc=(-1.2, 2.0, 11.8),
             target_loc=(0, 22, 0.5),
             lens=28)

# ── Render ───────────────────────────────────────────────────
scene.frame_set(1)
scene.render.filepath = "/Users/jmordetsky/directors-chair/assets/generated/videos/raider_ambush_v2/layouts/layout_010.png"
bpy.ops.render.render(write_still=True)
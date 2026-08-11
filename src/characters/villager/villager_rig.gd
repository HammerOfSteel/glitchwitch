class_name VillagerRig
extends RefCounted
## Builds the villager joint hierarchy from primitive meshes, per
## docs/superpowers/specs/2026-08-10-villager-rig-system-design.md §2.
## VillagerRig is the sole owner of primitive creation and UV-stamping —
## no other module touches mesh geometry or UVs.

const SKIN_SHADE := 3
const CLOTHING_SHADE := 2
const HAIR_SHADE := 1

# Base (height_scale = 1.0, build_scale = 1.0) dimensions in meters.
const TORSO_RADIUS := 0.14
const TORSO_HEIGHT := 0.42
const HEAD_RADIUS := 0.11
const ARM_RADIUS := 0.045
const ARM_LENGTH := 0.30
const LEG_RADIUS := 0.06
const LEG_LENGTH := 0.42
const HAND_RADIUS := 0.035
const HAIR_RADIUS := 0.09

var root: Node3D
var sockets: Dictionary = {}  # StringName -> Node3D


static func build(dna: VillagerDna) -> VillagerRig:
	var rig := VillagerRig.new()
	var h := dna.height_scale
	var b := dna.build_scale
	var leg_length := LEG_LENGTH * h
	var torso_height := TORSO_HEIGHT * h

	rig.root = Node3D.new()
	rig.root.name = "VillagerRoot"

	var torso := MeshInstance3D.new()
	torso.name = "torso"
	var torso_mesh := CapsuleMesh.new()
	torso_mesh.radius = TORSO_RADIUS * b
	torso_mesh.height = torso_height
	torso.mesh = PaletteUv.stamp_mesh(torso_mesh, dna.clothing_ramp, CLOTHING_SHADE)
	torso.position = Vector3(0.0, leg_length + torso_height / 2.0, 0.0)
	rig.root.add_child(torso)

	var neck := Node3D.new()
	neck.name = "neck"
	neck.position = Vector3(0.0, torso_height / 2.0, 0.0)
	torso.add_child(neck)

	var head := MeshInstance3D.new()
	head.name = "head"
	var head_mesh := SphereMesh.new()
	head_mesh.radius = HEAD_RADIUS * b
	head_mesh.height = HEAD_RADIUS * b * 2.0
	head.mesh = PaletteUv.stamp_mesh(head_mesh, dna.skin_ramp, SKIN_SHADE)
	head.position = Vector3(0.0, HEAD_RADIUS * b, 0.0)
	neck.add_child(head)

	var head_top := Node3D.new()
	head_top.name = "head_top"
	head_top.position = Vector3(0.0, HEAD_RADIUS * b, 0.0)
	head.add_child(head_top)
	rig.sockets[&"head_top"] = head_top

	var hair := MeshInstance3D.new()
	hair.name = "hair"
	var hair_mesh := SphereMesh.new()
	hair_mesh.radius = HAIR_RADIUS * b
	hair_mesh.height = HAIR_RADIUS * b * 1.2
	hair.mesh = PaletteUv.stamp_mesh(hair_mesh, dna.hair_ramp, HAIR_SHADE)
	hair.scale = Vector3(1.0, 0.65, 1.0)
	head_top.add_child(hair)

	for side in [-1.0, 1.0]:
		var suffix := "_l" if side < 0.0 else "_r"
		var shoulder := Node3D.new()
		shoulder.name = "shoulder%s" % suffix
		shoulder.position = Vector3(side * TORSO_RADIUS * b, torso_height / 2.0, 0.0)
		shoulder.scale = Vector3(side, 1.0, 1.0)
		torso.add_child(shoulder)

		var elbow := MeshInstance3D.new()
		elbow.name = "elbow%s" % suffix
		var arm_mesh := CapsuleMesh.new()
		arm_mesh.radius = ARM_RADIUS * b
		arm_mesh.height = ARM_LENGTH * h
		elbow.mesh = PaletteUv.stamp_mesh(arm_mesh, dna.clothing_ramp, CLOTHING_SHADE)
		elbow.position = Vector3(0.0, -ARM_LENGTH * h / 2.0, 0.0)
		shoulder.add_child(elbow)

		var hand := MeshInstance3D.new()
		hand.name = "hand%s" % suffix
		var hand_mesh := SphereMesh.new()
		hand_mesh.radius = HAND_RADIUS * b
		hand_mesh.height = HAND_RADIUS * b * 2.0
		hand.mesh = PaletteUv.stamp_mesh(hand_mesh, dna.skin_ramp, SKIN_SHADE)
		hand.position = Vector3(0.0, -ARM_LENGTH * h / 2.0, 0.0)
		elbow.add_child(hand)
		rig.sockets[StringName("hand%s" % suffix)] = hand

		var hip := Node3D.new()
		hip.name = "hip%s" % suffix
		hip.position = Vector3(side * TORSO_RADIUS * b * 0.6, -torso_height / 2.0, 0.0)
		hip.scale = Vector3(side, 1.0, 1.0)
		torso.add_child(hip)

		var knee := MeshInstance3D.new()
		knee.name = "knee%s" % suffix
		var leg_mesh := CapsuleMesh.new()
		leg_mesh.radius = LEG_RADIUS * b
		leg_mesh.height = leg_length
		knee.mesh = PaletteUv.stamp_mesh(leg_mesh, dna.clothing_ramp, CLOTHING_SHADE)
		knee.position = Vector3(0.0, -leg_length / 2.0, 0.0)
		hip.add_child(knee)

	return rig

extends GdUnitTestSuite
## VillagerRig: joint names present, mirrored L/R joints inverted,
## no dangling nodes after freeing.

const EXPECTED_JOINTS := [
	"torso", "neck", "head", "head_top",
	"shoulder_l", "shoulder_r", "elbow_l", "elbow_r", "hand_l", "hand_r",
	"hip_l", "hip_r", "knee_l", "knee_r",
]


func test_build_produces_all_expected_joints() -> void:
	var dna := VillagerDna.random(7)
	var rig := VillagerRig.build(dna)
	auto_free(rig.root)
	for joint_name in EXPECTED_JOINTS:
		assert_object(rig.root.find_child(joint_name, true, false)) \
			.override_failure_message("missing joint: %s" % joint_name).is_not_null()


func test_mirrored_joints_have_inverted_scale_x() -> void:
	var dna := VillagerDna.random(7)
	var rig := VillagerRig.build(dna)
	auto_free(rig.root)
	var left := rig.root.find_child("shoulder_l", true, false) as Node3D
	var right := rig.root.find_child("shoulder_r", true, false) as Node3D
	assert_float(left.scale.x * right.scale.x).is_less(0.0)


func test_hips_are_children_of_torso() -> void:
	# Pins the spec §2 hierarchy exactly: hip_l/hip_r hang off torso (like
	# shoulder_l/shoulder_r), not directly off root — regression guard for
	# a prior bug where hips were parented to root instead.
	var dna := VillagerDna.random(7)
	var rig := VillagerRig.build(dna)
	auto_free(rig.root)
	var torso := rig.root.find_child("torso", true, false) as Node3D
	var hip_l := rig.root.find_child("hip_l", true, false) as Node3D
	var hip_r := rig.root.find_child("hip_r", true, false) as Node3D
	assert_object(hip_l.get_parent()).is_equal(torso)
	assert_object(hip_r.get_parent()).is_equal(torso)


func test_body_meshes_are_stamped_with_expected_ramps() -> void:
	var dna := VillagerDna.random(7)
	var rig := VillagerRig.build(dna)
	auto_free(rig.root)
	var head := rig.root.find_child("head", true, false) as MeshInstance3D
	var torso := rig.root.find_child("torso", true, false) as MeshInstance3D
	var expected_skin_uv := PaletteUv.uv_for(dna.skin_ramp, 3)
	var expected_clothing_uv := PaletteUv.uv_for(dna.clothing_ramp, 2)
	var head_uvs: PackedVector2Array = head.mesh.surface_get_arrays(0)[Mesh.ARRAY_TEX_UV]
	var torso_uvs: PackedVector2Array = torso.mesh.surface_get_arrays(0)[Mesh.ARRAY_TEX_UV]
	assert_vector(head_uvs[0]).is_equal(expected_skin_uv)
	assert_vector(torso_uvs[0]).is_equal(expected_clothing_uv)


func test_hair_exists_under_head_top_and_is_stamped_with_hair_ramp() -> void:
	# v1's only socket-attached part — pins both its existence (it's easy
	# to accidentally omit) and its shade (hair always uses shade 1, per
	# the spec's fixed per-part shade table).
	var dna := VillagerDna.random(7)
	var rig := VillagerRig.build(dna)
	auto_free(rig.root)
	var head_top := rig.root.find_child("head_top", true, false) as Node3D
	var hair := head_top.find_child("hair", true, false) as MeshInstance3D
	assert_object(hair).override_failure_message("missing hair mesh under head_top").is_not_null()
	var expected_hair_uv := PaletteUv.uv_for(dna.hair_ramp, 1)
	var hair_uvs: PackedVector2Array = hair.mesh.surface_get_arrays(0)[Mesh.ARRAY_TEX_UV]
	assert_vector(hair_uvs[0]).is_equal(expected_hair_uv)


func test_sockets_dictionary_has_v1_entries() -> void:
	var dna := VillagerDna.random(7)
	var rig := VillagerRig.build(dna)
	auto_free(rig.root)
	assert_bool(rig.sockets.has(&"head_top")).is_true()
	assert_bool(rig.sockets.has(&"hand_l")).is_true()
	assert_bool(rig.sockets.has(&"hand_r")).is_true()


func test_freeing_root_leaves_no_dangling_children() -> void:
	var dna := VillagerDna.random(7)
	var rig := VillagerRig.build(dna)
	var root := rig.root
	assert_bool(is_instance_valid(root)).is_true()
	root.queue_free()
	await get_tree().process_frame
	# queue_free() defers actual deletion by one frame; after that frame the
	# instance itself (and, transitively, every child freed alongside it)
	# must be gone — this is the reliable way to assert cleanup in Godot,
	# unlike checking get_child_count() on an object that may already be
	# invalid.
	assert_bool(is_instance_valid(root)).is_false()

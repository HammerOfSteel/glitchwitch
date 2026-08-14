extends GdUnitTestSuite
## VillagerAnimator: idle/walk states drive joint rotation over time,
## unknown states fall back to idle.


func _build_animator() -> Array:
	var dna := VillagerDna.random(3)
	var rig := VillagerRig.build(dna)
	auto_free(rig.root)
	var animator := VillagerAnimator.new(rig)
	return [rig, animator]


func test_unknown_state_falls_back_to_idle() -> void:
	var pair := _build_animator()
	var animator: VillagerAnimator = pair[1]
	animator.set_motion_state(&"somersault")
	assert_str(String(animator.current_motion_state())).is_equal("idle")


func test_walk_state_changes_shoulder_rotation_over_time() -> void:
	var pair := _build_animator()
	var rig: VillagerRig = pair[0]
	var animator: VillagerAnimator = pair[1]
	animator.set_motion_state(&"walk")
	var shoulder := rig.root.find_child("shoulder_l", true, false) as Node3D
	var before := shoulder.rotation.x
	for i in range(10):
		animator.update(0.1)
	var after := shoulder.rotation.x
	assert_float(before).is_not_equal(after)


func test_walk_state_changes_hip_rotation_over_time() -> void:
	var pair := _build_animator()
	var rig: VillagerRig = pair[0]
	var animator: VillagerAnimator = pair[1]
	animator.set_motion_state(&"walk")
	var hip := rig.root.find_child("hip_l", true, false) as Node3D
	var before := hip.rotation.x
	for i in range(10):
		animator.update(0.1)
	var after := hip.rotation.x
	assert_float(before).is_not_equal(after)


func test_idle_state_still_animates_subtly() -> void:
	var pair := _build_animator()
	var rig: VillagerRig = pair[0]
	var animator: VillagerAnimator = pair[1]
	animator.set_motion_state(&"idle")
	var torso := rig.root.find_child("torso", true, false) as Node3D
	var before := torso.scale.y
	for i in range(10):
		animator.update(0.1)
	var after := torso.scale.y
	assert_float(before).is_not_equal(after)


func test_idle_head_bob_animates_head_position() -> void:
	var pair := _build_animator()
	var rig: VillagerRig = pair[0]
	var animator: VillagerAnimator = pair[1]
	animator.set_motion_state(&"idle")
	var head := rig.root.find_child("head", true, false) as Node3D
	var before := head.position.y
	for i in range(10):
		animator.update(0.1)
	var after := head.position.y
	assert_float(before).is_not_equal(after)

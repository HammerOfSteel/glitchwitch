extends GdUnitTestSuite
## RiggedNpc: a rigged+animated background NPC (skeleton + AnimationPlayer),
## the animated counterpart to StaticNpc for Meshy AI exports that do ship
## bones/clips (Ansel Rowe the postman, Torben Ask the forester — see
## docs/character-inventory.md). Plays a looping "idle" clip and exposes
## the same "Interactable + DialogueRunner.start()" wiring StaticNpc uses,
## so rigged and static NPCs plug into a zone identically.

const TEST_MESH_PATH := "res://assets/thirdparty/meshy-ai/NPCs/rigged/ansel_rowe/ansel_rowe.glb"
const TEST_DIALOGUE_PATH := "res://data/dialogue/villager_a.json"


func _build_npc() -> RiggedNpc:
	var npc := RiggedNpc.new()
	npc.mesh_scene_path = TEST_MESH_PATH
	npc.display_name = "Test Postman"
	npc.dialogue_path = TEST_DIALOGUE_PATH
	auto_free(npc)
	return npc


func test_instances_mesh_with_a_skeleton_and_animation_player() -> void:
	var npc := _build_npc()
	add_child(npc)
	await get_tree().process_frame

	var meshes := npc.find_children("*", "MeshInstance3D", true, false)
	(
		assert_int(meshes.size())
		. override_failure_message("expected the NPC mesh to be instanced")
		. is_greater(0)
	)

	var players := npc.find_children("*", "AnimationPlayer", true, false)
	(
		assert_int(players.size())
		. override_failure_message(
			"expected a rigged NPC to have an AnimationPlayer (unlike StaticNpc)"
		)
		. is_equal(1)
	)


func test_plays_idle_clip_on_ready() -> void:
	var npc := _build_npc()
	add_child(npc)
	await get_tree().process_frame

	var players := npc.find_children("*", "AnimationPlayer", true, false)
	var anim := players[0] as AnimationPlayer
	assert_str(anim.current_animation).is_equal("idle")
	assert_bool(anim.is_playing()).is_true()


func test_has_exactly_one_talk_interactable() -> void:
	var npc := _build_npc()
	add_child(npc)
	await get_tree().process_frame

	var interactables := npc.find_children("*", "Interactable", true, false)
	assert_int(interactables.size()).is_equal(1)
	var talk := interactables[0] as Interactable
	assert_str(talk.verb).is_equal("Talk")
	assert_str(talk.display_name).is_equal("Test Postman")


func test_mesh_feet_rest_on_the_ground_not_sunk_or_floating() -> void:
	# Rigged Meshy exports' own root sits at the feet already (unlike the
	# static export's vertical-center pivot — see test_static_npc.gd), but
	# this is asserted directly rather than assumed, per the same
	# ground-sink bug class already hit once this session.
	var npc := _build_npc()
	add_child(npc)
	await get_tree().process_frame

	var lowest_y := INF
	for found in npc.find_children("*", "MeshInstance3D", true, false):
		var mi := found as MeshInstance3D
		var aabb := mi.get_aabb()
		for corner_index in range(8):
			var corner := (
				aabb.position
				+ Vector3(
					aabb.size.x * float(corner_index & 1),
					aabb.size.y * float((corner_index >> 1) & 1),
					aabb.size.z * float((corner_index >> 2) & 1)
				)
			)
			var in_npc_space: Vector3 = npc.to_local(mi.to_global(corner))
			lowest_y = min(lowest_y, in_npc_space.y)

	var message := "expected the mesh's lowest point to rest at npc-local y=0 (got %.3f)" % lowest_y
	assert_float(lowest_y).override_failure_message(message).is_equal_approx(0.0, 0.05)


func test_interacting_starts_dialogue() -> void:
	var npc := _build_npc()
	add_child(npc)
	await get_tree().process_frame

	var talk := npc.find_children("*", "Interactable", true, false)[0] as Interactable
	talk.interact(self)
	assert_bool(DialogueRunner.is_active()).is_true()


func test_with_no_patrol_points_stays_in_place_playing_idle() -> void:
	var npc := _build_npc()
	add_child(npc)
	await get_tree().process_frame
	var before := npc.position
	for i in range(10):
		npc._process(0.1)
	assert_vector(npc.position).is_equal_approx(before, Vector3(0.001, 0.001, 0.001))
	var anim := npc.find_children("*", "AnimationPlayer", true, false)[0] as AnimationPlayer
	assert_str(anim.current_animation).is_equal("idle")


func test_patrols_between_waypoints_using_walk_clip() -> void:
	var npc := _build_npc()
	npc.patrol_points = [Vector3(5, 0, 0), Vector3(10, 0, 0)]
	npc.patrol_speed = 2.0
	add_child(npc)
	await get_tree().process_frame

	var before := npc.position
	for i in range(10):
		npc._process(0.1)
	var after := npc.position
	(
		assert_bool(before.is_equal_approx(after))
		. override_failure_message("expected patrolling to move the NPC toward its next waypoint")
		. is_false()
	)
	# Moving toward Vector3(5, 0, 0) from the origin — x should have increased.
	assert_float(after.x).is_greater(before.x)

	var anim := npc.find_children("*", "AnimationPlayer", true, false)[0] as AnimationPlayer
	assert_str(anim.current_animation).is_equal("walk")


func test_stops_and_faces_interactor_when_interacted() -> void:
	var npc := _build_npc()
	npc.patrol_points = [Vector3(5, 0, 0), Vector3(10, 0, 0)]
	npc.patrol_speed = 2.0
	add_child(npc)
	await get_tree().process_frame
	for i in range(5):
		npc._process(0.1)

	var interactor := Node3D.new()
	auto_free(interactor)
	add_child(interactor)
	interactor.global_position = npc.global_position + Vector3(3, 0, 0)

	var talk := npc.find_children("*", "Interactable", true, false)[0] as Interactable
	talk.interact(interactor)

	var position_after_interact := npc.position
	for i in range(5):
		npc._process(0.1)
	(
		assert_vector(npc.position)
		. override_failure_message("expected the NPC to stop patrolling while talking")
		. is_equal_approx(position_after_interact, Vector3(0.001, 0.001, 0.001))
	)

	# Facing the interactor: -Z (forward) should point roughly toward it.
	var to_interactor := (interactor.global_position - npc.global_position).normalized()
	var forward := -npc.global_transform.basis.z
	(
		assert_float(forward.dot(to_interactor))
		. override_failure_message("expected the NPC to rotate to face the interactor")
		. is_greater(0.9)
	)

	var anim := npc.find_children("*", "AnimationPlayer", true, false)[0] as AnimationPlayer
	assert_str(anim.current_animation).is_equal("idle")


func test_resumes_patrolling_after_dialogue_ends() -> void:
	var npc := _build_npc()
	npc.patrol_points = [Vector3(5, 0, 0), Vector3(10, 0, 0)]
	npc.patrol_speed = 2.0
	add_child(npc)
	await get_tree().process_frame

	var interactor := Node3D.new()
	auto_free(interactor)
	add_child(interactor)
	interactor.global_position = npc.global_position + Vector3(3, 0, 0)

	var talk := npc.find_children("*", "Interactable", true, false)[0] as Interactable
	talk.interact(interactor)
	assert_bool(DialogueRunner.is_active()).is_true()

	DialogueRunner.ended.emit()
	await get_tree().process_frame

	var before := npc.position
	for i in range(10):
		npc._process(0.1)
	(
		assert_bool(before.is_equal_approx(npc.position))
		. override_failure_message("expected the NPC to resume patrolling once dialogue ends")
		. is_false()
	)


func test_mesh_scale_defaults_to_one() -> void:
	var npc := _build_npc()
	add_child(npc)
	await get_tree().process_frame

	var body := npc.get_child(0) as Node3D
	(
		assert_vector(body.scale)
		. override_failure_message("expected the mesh body to be unscaled by default")
		. is_equal_approx(Vector3.ONE, Vector3.ONE * 0.001)
	)


func test_mesh_scale_export_scales_the_instanced_body() -> void:
	var npc := RiggedNpc.new()
	npc.mesh_scene_path = TEST_MESH_PATH
	npc.display_name = "Test Forester"
	npc.dialogue_path = TEST_DIALOGUE_PATH
	npc.mesh_scale = 1.3
	auto_free(npc)
	add_child(npc)
	await get_tree().process_frame

	var body := npc.get_child(0) as Node3D
	(
		assert_vector(body.scale)
		. override_failure_message("expected mesh_scale to uniformly scale the instanced body")
		. is_equal_approx(Vector3.ONE * 1.3, Vector3.ONE * 0.001)
	)


func after_test() -> void:
	DialogueRunner.flags = {}
	DialogueRunner._graph = null
	DialogueRunner._current_node_id = ""
	DialogueRunner._voice_seed = 0

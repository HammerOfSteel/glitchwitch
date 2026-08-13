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


func after_test() -> void:
	DialogueRunner.flags = {}
	DialogueRunner._graph = null
	DialogueRunner._current_node_id = ""
	DialogueRunner._voice_seed = 0

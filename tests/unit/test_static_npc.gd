extends GdUnitTestSuite
## StaticNpc: a non-rigged, static-mesh NPC that still reads as "alive"
## via a hand-authored Node3D transform bob/sway (no bones/AnimationPlayer),
## exposes a Talk Interactable, and starts dialogue on interact.

const TEST_MESH_PATH := "res://assets/thirdparty/meshy-ai/NPCs/villager_A_static_meshy.glb"
const TEST_DIALOGUE_PATH := "res://data/dialogue/villager_a.json"


func _build_npc() -> StaticNpc:
	var npc := StaticNpc.new()
	npc.mesh_scene_path = TEST_MESH_PATH
	npc.display_name = "Test Villager"
	npc.dialogue_path = TEST_DIALOGUE_PATH
	auto_free(npc)
	return npc


func test_instances_mesh_as_a_child() -> void:
	var npc := _build_npc()
	add_child(npc)
	await get_tree().process_frame

	var meshes := npc.find_children("*", "MeshInstance3D", true, false)
	(
		assert_int(meshes.size())
		. override_failure_message(
			"expected the static villager mesh to be instanced under StaticNpc"
		)
		. is_greater(0)
	)


func test_has_exactly_one_talk_interactable() -> void:
	var npc := _build_npc()
	add_child(npc)
	await get_tree().process_frame

	var interactables := npc.find_children("*", "Interactable", true, false)
	assert_int(interactables.size()).is_equal(1)
	var talk := interactables[0] as Interactable
	assert_str(talk.verb).is_equal("Talk")
	assert_str(talk.display_name).is_equal("Test Villager")


func test_idle_motion_bobs_and_sways_the_mesh_without_bones() -> void:
	var npc := _build_npc()
	add_child(npc)
	await get_tree().process_frame

	var mesh_root := npc.get_child(0) as Node3D
	assert_object(mesh_root).is_not_null()
	# No AnimationPlayer at all — the "idle" motion must be a plain
	# Node3D transform tween/sine, not a skeletal clip.
	var players := npc.find_children("*", "AnimationPlayer", true, false)
	assert_int(players.size()).is_equal(0)

	var before_pos := mesh_root.position
	var before_rot := mesh_root.rotation
	for i in range(30):
		npc._process(0.1)
	var after_pos := mesh_root.position
	var after_rot := mesh_root.rotation

	(
		assert_bool(before_pos.is_equal_approx(after_pos) and before_rot.is_equal_approx(after_rot))
		. override_failure_message("expected idle bob/sway to change the mesh transform over time")
		. is_false()
	)


func test_mesh_feet_rest_on_the_ground_not_sunk_or_floating() -> void:
	# The static Meshy export's own origin sits at its vertical center (its
	# accessor bounds are roughly y ∈ [-0.95, 0.95]), not at its feet like a
	# rigged export's root — without a computed ground lift, half the model
	# renders sunk below the floor. StaticNpc must lift the mesh so its
	# lowest vertex sits at y = 0 (npc's own origin), regardless of the
	# source mesh's own pivot.
	var npc := _build_npc()
	add_child(npc)
	await get_tree().process_frame

	var mesh_root := npc.get_child(0) as Node3D
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

	var message := (
		"expected the mesh's lowest point to rest at npc-local y=0 (got %.3f) — " % lowest_y
		+ "half the model is sunk into the ground"
	)
	# One process_frame may already have applied a fraction of the idle bob
	# (± bob_height) on top of the ground lift, so tolerance must cover it.
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

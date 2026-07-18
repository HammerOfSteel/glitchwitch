extends GdUnitTestSuite
## Interaction: scoring, cone filtering, hysteresis, prompts, dispatch.

const PLAYER_SCENE := "res://src/player/player.tscn"


func _make_item(pos: Vector3, item_priority: int = 0, item_name: String = "") -> Interactable:
	var item := Interactable.new()
	item.position = pos
	item.focus_priority = item_priority
	item.display_name = item_name
	return item


func _spawn_world(items: Array) -> Dictionary:
	var arena := Node3D.new()
	auto_free(arena)
	var player: Player = (load(PLAYER_SCENE) as PackedScene).instantiate()
	player.input_enabled = false
	arena.add_child(player)
	for item in items:
		arena.add_child(item)
	return {"arena": arena, "player": player}


func test_score_prefers_near_centered_important() -> void:
	var near := FocusResolver.score(1.0, 1.0, 0)
	var far := FocusResolver.score(2.4, 1.0, 0)
	var off_axis := FocusResolver.score(1.0, 0.5, 0)
	var important := FocusResolver.score(1.0, 1.0, 3)
	assert_float(near).is_less(far)
	assert_float(near).is_less(off_axis)
	assert_float(important).is_less(near)


func test_focus_picks_item_in_front_within_reach() -> void:
	# player faces -Z by default
	var front := _make_item(Vector3(0, 1, -1.5))
	var behind := _make_item(Vector3(0, 1, 1.5))
	var too_far := _make_item(Vector3(0, 1, -6.0))
	var world := _spawn_world([front, behind, too_far])
	var runner := scene_runner(world.arena)
	await runner.simulate_frames(15)

	var resolver := world.player.get_node("%FocusResolver") as FocusResolver
	assert_object(resolver.focused()).is_same(front)
	assert_bool(front.is_focused()).is_true()
	assert_bool(behind.is_focused()).is_false()


func test_priority_wins_between_similar_candidates() -> void:
	var plain := _make_item(Vector3(0.2, 1, -1.4))
	var important := _make_item(Vector3(-0.2, 1, -1.5), 3)
	var world := _spawn_world([plain, important])
	var runner := scene_runner(world.arena)
	await runner.simulate_frames(15)

	var resolver := world.player.get_node("%FocusResolver") as FocusResolver
	assert_object(resolver.focused()).is_same(important)


func test_hysteresis_keeps_focus_against_marginal_rival() -> void:
	var held := _make_item(Vector3(0, 1, -1.5))
	var world := _spawn_world([held])
	var runner := scene_runner(world.arena)
	await runner.simulate_frames(15)
	var resolver := world.player.get_node("%FocusResolver") as FocusResolver
	assert_object(resolver.focused()).is_same(held)

	# a rival marginally better (5% closer) must NOT steal focus...
	var rival := _make_item(Vector3(0, 1, -1.42))
	world.arena.add_child(rival)
	await runner.simulate_frames(15)
	assert_object(resolver.focused()).is_same(held)

	# ...but a clearly better one (much closer) must
	var winner := _make_item(Vector3(0, 1, -0.7))
	world.arena.add_child(winner)
	await runner.simulate_frames(15)
	assert_object(resolver.focused()).is_same(winner)


func test_disabled_items_are_ignored_and_focus_clears() -> void:
	var only := _make_item(Vector3(0, 1, -1.5))
	var world := _spawn_world([only])
	var runner := scene_runner(world.arena)
	await runner.simulate_frames(15)
	var resolver := world.player.get_node("%FocusResolver") as FocusResolver
	assert_object(resolver.focused()).is_same(only)

	only.enabled = false
	await runner.simulate_frames(15)
	assert_object(resolver.focused()).is_null()
	assert_bool(only.is_focused()).is_false()


func test_prompt_shows_verb_and_name_then_hides() -> void:
	var item := _make_item(Vector3(0, 1, -1.5), 0, "a seam in the world")
	item.verb = "Observe"
	var world := _spawn_world([item])
	var runner := scene_runner(world.arena)
	await runner.simulate_frames(15)

	var prompt := world.player.get_node("%InteractPrompt") as InteractPrompt
	assert_bool(prompt.visible).is_true()
	assert_str(prompt.text).contains("Observe")
	assert_str(prompt.text).contains("a seam in the world")

	item.enabled = false
	await runner.simulate_frames(15)
	assert_bool(prompt.visible).is_false()


func test_interact_routes_to_focused_item_only_when_enabled() -> void:
	var item := _make_item(Vector3(0, 1, -1.5))
	var world := _spawn_world([item])
	var runner := scene_runner(world.arena)
	await runner.simulate_frames(15)

	var hits: Array = []
	item.interacted.connect(func(by: Node) -> void: hits.append(by))
	var resolver := world.player.get_node("%FocusResolver") as FocusResolver
	resolver.interact_focused(world.player)
	assert_int(hits.size()).is_equal(1)
	assert_object(hits[0]).is_same(world.player)

	item.enabled = false
	resolver.interact_focused(world.player)
	assert_int(hits.size()).is_equal(1)

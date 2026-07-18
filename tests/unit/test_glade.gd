extends GdUnitTestSuite
## Sandbox glade smoke: the playable slice assembles with player, seam stone,
## palette-dressed props, and a working seam interaction.

const GLADE_SCENE := "res://src/sandbox/glade.tscn"


func test_glade_assembles_with_player_and_seam() -> void:
	var runner := scene_runner(GLADE_SCENE)
	await runner.simulate_frames(10)
	var glade := runner.scene()

	assert_object(glade.get_node_or_null("Player")).is_not_null()

	var stone := glade.get_node("%SeamStone") as MeshInstance3D
	assert_int(int(stone.layers)).is_equal(2)
	(
		assert_object(stone.material_override)
		. override_failure_message("seam stone lost its glitch material")
		. is_not_null()
	)

	var palette_material: Material = load(PaletteApply.PALETTE_MATERIAL_PATH)
	assert_object(stone.material_override).is_not_same(palette_material)

	var dressed := 0
	for found in glade.find_children("*", "MeshInstance3D", true, false):
		if (found as MeshInstance3D).material_override == palette_material:
			dressed += 1
	assert_int(dressed).override_failure_message("props missing palette").is_greater(20)


func test_seam_interactable_is_configured() -> void:
	var runner := scene_runner(GLADE_SCENE)
	await runner.simulate_frames(5)
	var seam := runner.scene().get_node("%SeamInteractable") as Interactable

	assert_object(seam).is_not_null()
	assert_str(seam.verb).is_equal("Observe")
	assert_str(seam.display_name).is_equal("a seam in the world")
	assert_int(seam.focus_priority).is_equal(1)
	assert_bool(seam.is_in_group(&"interactables")).is_true()


func test_seam_spins_when_observed() -> void:
	var runner := scene_runner(GLADE_SCENE)
	await runner.simulate_frames(5)
	var glade := runner.scene()
	var stone := glade.get_node("%SeamStone") as MeshInstance3D
	var seam := glade.get_node("%SeamInteractable") as Interactable

	var before := stone.rotation.y
	seam.interact(glade)
	var spun := false
	for _i in range(60):
		await runner.simulate_frames(10)
		if absf(stone.rotation.y - before) > 0.5:
			spun = true
			break
	assert_bool(spun).override_failure_message("seam stone never answered").is_true()

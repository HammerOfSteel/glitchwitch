extends GdUnitTestSuite
## InteractPrompt: covers the dialogue-overlap fix directly (spec §4) —
## force_hide() must hide the prompt even while it's already visible, and
## on_focus_changed() must be able to re-show it afterward without waiting
## for a fresh focus_changed event.


func test_force_hide_hides_prompt_even_when_already_visible() -> void:
	var prompt := InteractPrompt.new()
	auto_free(prompt)
	var item := Interactable.new()
	auto_free(item)
	prompt.on_focus_changed(item)
	assert_bool(prompt.visible).is_true()
	prompt.force_hide()
	assert_bool(prompt.visible).is_false()


func test_on_focus_changed_reshows_prompt_after_force_hide() -> void:
	var prompt := InteractPrompt.new()
	auto_free(prompt)
	var item := Interactable.new()
	auto_free(item)
	prompt.on_focus_changed(item)
	prompt.force_hide()
	prompt.on_focus_changed(item)
	assert_bool(prompt.visible).is_true()

class_name VillagerBuildResult
extends RefCounted
## Bundle returned by a BodySynthesizer-shaped build() function (currently
## only HumanSynth). See
## docs/superpowers/specs/2026-08-10-villager-rig-system-design.md §3.

var root: Node3D
var rig: VillagerRig
var sockets: Dictionary  # StringName -> Node3D

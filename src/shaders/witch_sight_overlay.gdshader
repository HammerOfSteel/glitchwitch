// Witch Sight overlay — a soft diagnostic lens: cool-to-magenta vignette,
// kept subtle so the world stays readable. Reduce-glitch mode (Phase 3)
// will lower intensity further.
shader_type canvas_item;

uniform float intensity: hint_range(0.0, 1.0) = 0.30;

void fragment() {
	vec2 centered = UV - vec2(0.5);
	float vignette = smoothstep(0.30, 0.78, length(centered));
	vec3 tint = mix(vec3(0.31, 0.85, 0.88), vec3(0.88, 0.31, 0.82), UV.y);
	COLOR = vec4(tint, vignette * intensity);
}

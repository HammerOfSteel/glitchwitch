// Glitch Witch toon shader — palette-atlas albedo, soft stepped ramp, gentle rim.
// The toy-render look: flat palette colors, 3-step light, warm shadow tint.
shader_type spatial;
render_mode cull_back, depth_draw_opaque, specular_disabled;

uniform sampler2D palette_tex: source_color, filter_nearest;
uniform float ramp_steps: hint_range(2.0, 4.0) = 3.0;
uniform float rim_strength: hint_range(0.0, 1.0) = 0.22;
uniform vec3 shadow_tint: source_color = vec3(0.58, 0.52, 0.62);

void fragment() {
	ALBEDO = texture(palette_tex, UV).rgb;
	ROUGHNESS = 1.0;
	SPECULAR = 0.0;
}

void light() {
	float ndotl = dot(NORMAL, LIGHT);
	float wrapped = clamp(ndotl * 0.5 + 0.5, 0.0, 1.0);
	float stepped = clamp(floor(wrapped * ramp_steps) / (ramp_steps - 1.0), 0.0, 1.0);
	vec3 lit = mix(ALBEDO * shadow_tint, ALBEDO, stepped);
	DIFFUSE_LIGHT += lit * ATTENUATION * LIGHT_COLOR / PI;
	float rim = pow(1.0 - clamp(dot(NORMAL, VIEW), 0.0, 1.0), 3.0);
	DIFFUSE_LIGHT += rim * rim_strength * ALBEDO * ATTENUATION * LIGHT_COLOR / PI;
}

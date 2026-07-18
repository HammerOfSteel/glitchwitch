// Inverted-hull outline — dark warm tone, never pure black (design bible).
shader_type spatial;
render_mode unshaded, cull_front, depth_draw_opaque;

uniform vec3 outline_color: source_color = vec3(0.16, 0.12, 0.10);
uniform float thickness: hint_range(0.0, 0.05) = 0.012;

void vertex() {
	VERTEX += NORMAL * thickness;
}

void fragment() {
	ALBEDO = outline_color;
}

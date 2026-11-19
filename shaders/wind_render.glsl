// 风场粒子渲染（参考着色器，与 regression.py 的 pack/unpack 共用同一套数学）
// u_wind: RG = u 分量高低字节，BA = v 分量高低字节；minV/maxV 与 tests.yaml 一致。

// ---- vertex ----
/*
attribute vec2 a_pos;      // 粒子位置（归一化经纬度）
attribute float a_seed;
uniform sampler2D u_wind;
uniform vec2 u_minV_maxV;  // (-60.0, 60.0)
uniform float u_dt;
varying float v_speed;

vec2 fetchWind(vec2 uv) {
    vec4 packed = texture2D(u_wind, uv);
    return unpackWind(packed, u_minV_maxV.x, u_minV_maxV.y);
}

void main() {
    vec2 wind = fetchWind(a_pos);
    vec2 pos = a_pos + wind * u_dt;
    v_speed = length(wind);
    gl_PointSize = 2.0;
    gl_Position = vec4(pos * 2.0 - 1.0, 0.0, 1.0);
}
*/

// ---- fragment ----
/*
precision mediump float;
varying float v_speed;

vec3 speedColor(float s) {
    // 0 m/s 蓝 -> 15 m/s 绿 -> 30 m/s 黄 -> 60 m/s 红
    vec3 c0 = vec3(0.10, 0.30, 0.90);
    vec3 c1 = vec3(0.10, 0.80, 0.30);
    vec3 c2 = vec3(0.95, 0.85, 0.10);
    vec3 c3 = vec3(0.90, 0.15, 0.10);
    float t = clamp(s / 60.0, 0.0, 1.0);
    vec3 c = mix(c0, c1, smoothstep(0.00, 0.25, t));
    c = mix(c, c2, smoothstep(0.25, 0.50, t));
    c = mix(c, c3, smoothstep(0.50, 1.00, t));
    return c;
}

void main() {
    gl_FragColor = vec4(speedColor(v_speed), 0.85);
}
*/

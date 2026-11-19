// GIS 风场 pack/unpack：把风速分量编码进纹理通道（每分量 16-bit = 高低字节）
// 与 regression.py 里的 pack/unpack 数学一致：
//   q = round((v - minV) / (maxV - minV) * 65535)
//   高字节 = floor(q / 256)，低字节 = q mod 256
// RG 通道存 u 分量，BA 通道存 v 分量。

float unpack16(vec2 bytes, float minV, float maxV) {
    float q = bytes.x * 255.0 * 256.0 + bytes.y * 255.0;
    return minV + q / 65535.0 * (maxV - minV);
}

vec2 pack16(float v, float minV, float maxV) {
    float q = floor(clamp((v - minV) / (maxV - minV), 0.0, 1.0) * 65535.0 + 0.5);
    return vec2(floor(q / 256.0) / 255.0, mod(q, 256.0) / 255.0);
}

vec4 packWind(vec2 wind, float minV, float maxV) {
    return vec4(pack16(wind.x, minV, maxV), pack16(wind.y, minV, maxV));
}

vec2 unpackWind(vec4 packed, float minV, float maxV) {
    return vec2(unpack16(packed.rg, minV, maxV), unpack16(packed.ba, minV, maxV));
}

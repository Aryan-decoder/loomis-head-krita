import math
from collections.abc import Sequence

from .euclid import Vector2, Vector3
from .geom_polyline import (
    EPS,
    clip_to_side_band,
    path_str,
    split_by_plane_facing,
    split_front_back,
)
from .linalg import (
    Poly2,
    Poly3,
    Quaternion,
    linspace,
    normalize,
    q_identity,
    q_normalize,
)


class LoomisHead3D:
    def __init__(self) -> None:
        self.radius: float = 1.0
        self.scale: float = 1.0
        self.side_cut: float = 0.66
        self.front_line_stroke: float = 5
        self.back_line_stroke: float = 5
        self.show_arrow: bool = True
        self.show_silhouette: bool = True
        self.show_side_rims: bool = True
        self.show_side_cross: bool = True
        self.stroke_color: str = "#6A54E7"
        self.q: Quaternion = q_identity()

    def set_quaternion(self, q: Quaternion) -> None:
        self.q = q_normalize(q)

    def set_scale(self, scale: float) -> None:
        self.scale = scale

    def set_sidecut(self, side_cut: float) -> None:
        self.side_cut = side_cut

    def set_front_line_stroke(self, front_line_stroke: float) -> None:
        self.front_line_stroke = front_line_stroke

    def set_back_line_stroke(self, back_line_stroke: float) -> None:
        self.back_line_stroke = back_line_stroke

    def set_arrow(self, enable: bool) -> None:
        self.show_arrow = enable

    def set_silhouette(self, enable: bool) -> None:
        self.show_silhouette = enable

    def set_side_rims(self, enable: bool) -> None:
        self.show_side_rims = enable

    def set_side_cross(self, enable: bool) -> None:
        self.show_side_cross = enable

    def set_stroke_color(self, color: str) -> None:
        self.stroke_color = color

    def _basis_from_nnormal(self, n: Vector3 | Sequence[float]) -> tuple[Vector3, Vector3]:
        nn = n if isinstance(n, Vector3) else Vector3(*n)
        nn = normalize(nn)

        axes = [Vector3(1.0, 0.0, 0.0), Vector3(0.0, 1.0, 0.0), Vector3(0.0, 0.0, 1.0)]
        a = min(axes, key=lambda ax: abs(nn.dot(ax)))

        u = normalize(nn.cross(a))
        v = nn.cross(u)
        return u, v

    def _circle_on_plane(
        self,
        normal: Vector3 | Sequence[float],
        center: Sequence[float],
        radius: float,
        samples: int = 256,
    ) -> Poly3:
        u, v = self._basis_from_nnormal(normal)
        cx, cy, cz = center
        pts: Poly3 = []
        for t in linspace(0.0, 2.0 * math.pi, samples, endpoint=False):
            c, s = math.cos(t), math.sin(t)
            p = Vector3(cx, cy, cz) + u * (c * radius) + v * (s * radius)
            pts.append(p)
        return pts

    def _to_camera(self, pts: Sequence[Vector3]) -> Poly3:
        q = self.q
        out: Poly3 = []
        for p in pts:
            pv = q * p
            out.append(pv)
        return out

    def _to_screen(
        self,
        pts_cam: Sequence[Vector3],
        w: float,
        h: float,
    ) -> Poly2:
        cx_val = w * 0.5
        cy_val = h * 0.5
        s = min(w, h) * 0.3 * self.scale
        xy: Poly2 = []
        for p in pts_cam:
            x_s = p.x * s + cx_val
            y_s = cy_val - p.y * s
            xy.append(Vector2(x_s, y_s))
        return xy

    def _emit_segments(
        self,
        segments: list[Poly3],
        width: float,
        height: float,
        front_paths: list[str],
        back_paths: list[str],
        plane_normal_cam: Vector3 | None = None,
    ) -> None:
        for segment in segments:
            segment_camera = self._to_camera(segment)
            if plane_normal_cam is None:
                fsegs, bsegs = split_front_back(segment_camera)
            else:
                fsegs, bsegs = split_by_plane_facing(segment_camera, plane_normal_cam)
            for s in bsegs:
                back_paths.append(path_str(self._to_screen(s, width, height)))
            for s in fsegs:
                front_paths.append(path_str(self._to_screen(s, width, height)))

    def build_svg(self, width: float, height: float, dash_back: str | None = "5,6", samples: int = 256) -> str:
        r = self.radius
        d = max(0.05, min(0.9, float(self.side_cut))) * r
        rim_r = math.sqrt(max(r * r - d * d, EPS))

        nx = Vector3(1.0, 0.0, 0.0)
        ny = Vector3(0.0, 1.0, 0.0)

        n_view = Vector3(0.0, 0.0, 1.0)
        n_sil_head = self.q.conjugated() * n_view

        n_plus_cam = self.q * nx
        n_minus_cam = self.q * (-nx)

        curves: list[Poly3] = []

        if self.show_silhouette:
            curves.append(self._circle_on_plane(n_sil_head, [0.0, 0.0, 0.0], r, samples))

        curves.append(self._circle_on_plane(nx, [0.0, 0.0, 0.0], r, samples))  # centerline
        curves.append(self._circle_on_plane(ny, [0.0, 0.0, 0.0], r, samples))  # equator

        rims_plus: list[Poly3] = []
        rims_minus: list[Poly3] = []

        if self.show_side_rims:
            rims_plus.append(self._circle_on_plane(nx, [d, 0.0, 0.0], rim_r, samples))
            rims_minus.append(self._circle_on_plane(nx, [-d, 0.0, 0.0], rim_r, samples))

        crosses_plus: list[Poly3] = []
        crosses_minus: list[Poly3] = []

        if self.show_side_cross:
            crosses_plus.extend(
                [
                    [Vector3(d, -rim_r, 0.0), Vector3(d, rim_r, 0.0)],
                    [Vector3(d, 0.0, -rim_r), Vector3(d, 0.0, rim_r)],
                ]
            )
            crosses_minus.extend(
                [
                    [Vector3(-d, -rim_r, 0.0), Vector3(-d, rim_r, 0.0)],
                    [Vector3(-d, 0.0, -rim_r), Vector3(-d, 0.0, rim_r)],
                ]
            )

        front_paths: list[str] = []
        back_paths: list[str] = []

        for c in curves:
            self._emit_segments(clip_to_side_band(c, d), width, height, front_paths, back_paths)
        for rim in rims_plus:
            self._emit_segments([rim], width, height, front_paths, back_paths, n_plus_cam)
        for rim in rims_minus:
            self._emit_segments([rim], width, height, front_paths, back_paths, n_minus_cam)
        for seg in crosses_plus:
            self._emit_segments([seg], width, height, front_paths, back_paths, n_plus_cam)
        for seg in crosses_minus:
            self._emit_segments([seg], width, height, front_paths, back_paths, n_minus_cam)

        arrow_d = ""
        if self.show_arrow:
            base2 = self._to_screen(self._to_camera([Vector3(0.0, 0.0, 0.0)]), width, height)[0]
            tip2 = self._to_screen(self._to_camera([Vector3(0.0, 0.0, 1.15 * r)]), width, height)[0]
            dv: Vector2 = tip2 - base2
            L = dv.magnitude()
            if L > 1.0:
                u = dv / L
                n = Vector2(-u.y, u.x)
                head_len = 0.04 * min(width, height)
                head_wid = 0.55 * head_len
                pL = tip2 - u * head_len + n * head_wid
                pR = tip2 - u * head_len - n * head_wid
                arrow_d = (
                    f"M {base2.x:.3f},{base2.y:.3f} L {tip2.x:.3f},{tip2.y:.3f} "
                    f"M {tip2.x:.3f},{tip2.y:.3f} L {pL.x:.3f},{pL.y:.3f} "
                    f"M {tip2.x:.3f},{tip2.y:.3f} L {pR.x:.3f},{pR.y:.3f} "
                )

        dash_attr = f' stroke-dasharray="{dash_back}"' if dash_back else ""
        svg: list[str] = [
            '<svg xmlns="http://www.w3.org/2000/svg">',
            f'<g title="head" fill="none" stroke="{self.stroke_color}">',
        ]

        if back_paths:
            svg.append(f'<path d="{"".join(back_paths)}" stroke-width="{self.back_line_stroke}"{dash_attr} opacity="0.6"/>')

        if front_paths:
            svg.append(f'<path d="{"".join(front_paths)}" stroke-width="{self.front_line_stroke}"/>')

        if self.show_arrow and arrow_d:
            svg.append(f'</g><g fill="none" title="arrow" stroke="{self.stroke_color}">')
            svg.append(f'<path d="{arrow_d}" stroke-width="{self.front_line_stroke + 1}"/>')

        svg.append("</g></svg>")
        return "".join(svg)

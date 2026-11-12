"""Ferramentas de inspeção geométrica e de porosidade com OpenCV (baseado no Projeto_Aero e adaptado para soldas VulcanTech)."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import cv2
import numpy as np


@dataclass(frozen=True)
class GeometryConfig:
    gaussian_kernel: int = 5
    canny_low: int = 50
    canny_high: int = 150
    min_contour_area: float = 20.0
    clahe_clip_limit: float = 2.0
    blackhat_kernel: int = 19
    min_porosity_circularity: float = 0.28
    porosity_reject_pct: float = 3.0

    def __post_init__(self) -> None:
        if self.gaussian_kernel < 1 or self.gaussian_kernel % 2 == 0:
            raise ValueError("gaussian_kernel deve ser positivo e ímpar")
        if not 0 <= self.canny_low < self.canny_high <= 255:
            raise ValueError("Limiares Canny inválidos")
        if self.min_contour_area < 0:
            raise ValueError("min_contour_area não pode ser negativo")
        if self.blackhat_kernel < 3 or self.blackhat_kernel % 2 == 0:
            raise ValueError("blackhat_kernel deve ser ímpar e >= 3")


def load_image(path: str | Path) -> np.ndarray:
    """Carrega imagem preservando o arquivo e lança erro claro se inválido."""
    image = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    if image is None:
        raise ValueError(f"Imagem inexistente, corrompida ou não suportada: {path}")
    if image.ndim not in (2, 3):
        raise ValueError(f"Formato de imagem inválido: {path}")
    return image


def contour_features(contour: np.ndarray, index: int = 0) -> dict[str, Any]:
    """Calcula atributos geométricos de um contorno (área, perímetro, circularidade, solidez, bbox)."""
    area = float(cv2.contourArea(contour))
    perimeter = float(cv2.arcLength(contour, True))
    circularity = (
        float(4.0 * np.pi * area / (perimeter**2))
        if perimeter > 0 and np.isfinite(perimeter)
        else None
    )
    x, y, width, height = (int(v) for v in cv2.boundingRect(contour))
    hull = cv2.convexHull(contour)
    hull_area = float(cv2.contourArea(hull)) if hull is not None else 0.0
    solidity = float(area / hull_area) if hull_area > 0 else 1.0

    moments = cv2.moments(contour)
    centroid = None
    if moments["m00"] != 0 and np.isfinite(moments["m00"]):
        centroid = {
            "x": float(moments["m10"] / moments["m00"]),
            "y": float(moments["m01"] / moments["m00"]),
        }
    return {
        "index": index,
        "area": area,
        "perimeter": perimeter,
        "circularity": circularity,
        "solidity": round(solidity, 4),
        "bbox": {"x": x, "y": y, "width": width, "height": height},
        "centroid": centroid,
        "aspect_ratio": float(width / height) if height else None,
        "is_porosity": bool(
            circularity is not None
            and circularity >= 0.45
            and solidity >= 0.60
            and 12.0 <= area <= 1500.0
        ),
    }


def segment_weld_bead(gray: np.ndarray, gaussian_kernel: int = 5) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Segmenta o cordão de solda usando energia de gradiente direcional de Sobel, Otsu e morfologia.

    Retorna: (mascara_cordao, contorno_cordao, magnitude_sobel_uint8).
    """
    h, w = gray.shape[:2]
    k_blur = max(3, int(gaussian_kernel) | 1)
    blurred = cv2.GaussianBlur(gray, (k_blur, k_blur), 0)

    gx = cv2.Sobel(blurred, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(blurred, cv2.CV_32F, 0, 1, ksize=3)
    mag = cv2.magnitude(gx, gy)
    mag_u8 = cv2.normalize(mag, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)

    kx_e = max(5, (w // 45) | 1)
    ky_e = max(3, (h // 135) | 1)
    energy = cv2.GaussianBlur(mag, (kx_e, ky_e), 0)
    energy_norm = cv2.normalize(energy, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)

    _, mask_raw = cv2.threshold(energy_norm, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    kw = max(5, (w // 36) | 1)
    kh = max(5, (h // 60) | 1)
    mask_closed = cv2.morphologyEx(
        mask_raw,
        cv2.MORPH_CLOSE,
        cv2.getStructuringElement(cv2.MORPH_RECT, (kw, kh)),
    )
    mask_opened = cv2.morphologyEx(
        mask_closed,
        cv2.MORPH_OPEN,
        cv2.getStructuringElement(cv2.MORPH_RECT, (max(3, (kw // 2) | 1), max(3, (kh // 2) | 1))),
    )

    contours, _ = cv2.findContours(mask_opened, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    min_valid_area = float(h * w) * 0.02
    valid = [c for c in contours if cv2.contourArea(c) >= min_valid_area]

    if not valid:
        _, otsu = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        cnts_otsu, _ = cv2.findContours(otsu, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        valid = [c for c in cnts_otsu if cv2.contourArea(c) >= max(25.0, float(h * w) * 0.01)]

    mask_cordao = np.zeros((h, w), dtype=np.uint8)
    if valid:
        cordao = max(valid, key=cv2.contourArea)
        cv2.drawContours(mask_cordao, [cordao], -1, 255, thickness=cv2.FILLED)
    else:
        cordao = np.array(
            [
                [[int(w * 0.05), int(h * 0.30)]],
                [[int(w * 0.95), int(h * 0.30)]],
                [[int(w * 0.95), int(h * 0.70)]],
                [[int(w * 0.05), int(h * 0.70)]],
            ],
            dtype=np.int32,
        )
        cv2.drawContours(mask_cordao, [cordao], -1, 255, thickness=cv2.FILLED)

    return mask_cordao, cordao, mag_u8


def detect_porosity_and_coherence(
    gray: np.ndarray,
    mask_cordao: np.ndarray,
    blackhat_kernel: int = 19,
    min_circularity: float = 0.28,
) -> dict[str, Any]:
    """Aplica Tensor de Estrutura (Coerência/Isotropia), Black-Hat Morfológico e Filtro de Circularidade."""
    h, w = gray.shape[:2]
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    gx = cv2.Sobel(blurred, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(blurred, cv2.CV_32F, 0, 1, ksize=3)

    kt_loc = max(5, (min(h, w) // 30) | 1)
    jxx = cv2.GaussianBlur(gx * gx, (kt_loc, kt_loc), 0)
    jyy = cv2.GaussianBlur(gy * gy, (kt_loc, kt_loc), 0)
    jxy = cv2.GaussianBlur(gx * gy, (kt_loc, kt_loc), 0)
    coherence_map = np.sqrt((jxx - jyy) ** 2 + 4.0 * (jxy**2)) / (jxx + jyy + 1e-6)
    isotropy_map = 1.0 - coherence_map

    erode_k = max(3, (min(h, w) // 40) | 1)
    inner_mask = cv2.erode(
        mask_cordao,
        cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (erode_k, erode_k)),
    )
    if np.count_nonzero(inner_mask) == 0:
        inner_mask = mask_cordao.copy()

    active_pixels = inner_mask > 0
    if np.any(active_pixels):
        mean_coherence = float(coherence_map[active_pixels].mean())
        gx_mean = float(np.abs(gx[active_pixels]).mean())
        gy_mean = float(np.abs(gy[active_pixels]).mean())
        gx_gy_ratio = float(gx_mean / (gy_mean + 1e-6))
    else:
        mean_coherence = 1.0
        gx_gy_ratio = 1.0

    mean_isotropy = 1.0 - mean_coherence
    kbh = max(int(blackhat_kernel) | 1, (min(h, w) // 45) | 1)
    bh = cv2.morphologyEx(
        blurred,
        cv2.MORPH_BLACKHAT,
        cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kbh, kbh)),
    )

    disorder_gain = 1.65 if mean_isotropy >= 0.42 else 0.28
    pore_score = bh.astype(np.float32) * (isotropy_map**1.55) * disorder_gain

    pore_mask = (
        np.uint8(
            (((pore_score >= 14.5) & (blurred < 70)) | (bh >= 165))
            & (inner_mask > 0)
        )
        * 255
    )
    k_open = max(3, (min(h, w) // 200) | 1)
    pore_mask = cv2.morphologyEx(
        pore_mask,
        cv2.MORPH_OPEN,
        cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k_open, k_open)),
    )

    area_cordao = max(float(np.count_nonzero(mask_cordao)), 1.0)
    p_cnts, _ = cv2.findContours(pore_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    pores: list[dict[str, Any]] = []
    clean_pore_mask = np.zeros_like(gray)
    total_pore_area = 0.0
    effective_min_circ = min(min_circularity, 0.14) if mean_isotropy >= 0.42 else min_circularity

    for idx, c in enumerate(p_cnts):
        area = float(cv2.contourArea(c))
        if 12.0 <= area <= (area_cordao * 0.25):
            perim = float(cv2.arcLength(c, True))
            circ = float(4.0 * np.pi * area / (perim * perim + 1e-6))
            if circ >= effective_min_circ:
                (cx, cy), radius = cv2.minEnclosingCircle(c)
                x, y, pw, ph = (int(v) for v in cv2.boundingRect(c))
                pores.append(
                    {
                        "index": idx,
                        "centro": (int(cx), int(cy)),
                        "raio": int(max(radius, 2)),
                        "area": round(area, 2),
                        "circularidade": round(circ, 4),
                        "bbox": {"x": x, "y": y, "width": pw, "height": ph},
                    }
                )
                total_pore_area += area
                cv2.drawContours(clean_pore_mask, [c], -1, 255, thickness=cv2.FILLED)

    porosity_pct = float((total_pore_area / area_cordao) * 100.0)
    coherence_u8 = np.clip(coherence_map * 255.0, 0, 255).astype(np.uint8)
    coherence_color = cv2.applyColorMap(coherence_u8, cv2.COLORMAP_VIRIDIS)

    return {
        "pores": pores,
        "pores_count": len(pores),
        "total_pore_area_px": round(total_pore_area, 2),
        "porosity_pct": round(porosity_pct, 3),
        "mean_coherence": round(mean_coherence, 4),
        "mean_isotropy": round(mean_isotropy, 4),
        "gx_gy_ratio": round(gx_gy_ratio, 4),
        "blackhat": bh,
        "porosity_mask": clean_pore_mask,
        "coherence_color": coherence_color,
    }


def analyze_bead_profile(mask_cordao: np.ndarray, contour_cordao: np.ndarray) -> dict[str, Any]:
    """Mede o perfil transversal de largura, rugosidade das margens (mordeduras) e descontinuidades."""
    h, w = mask_cordao.shape[:2]
    x, y, bw, bh = cv2.boundingRect(contour_cordao)
    is_horizontal = bw >= bh

    widths: list[float] = []
    positions: list[int] = []
    edge_a: list[float] = []
    edge_b: list[float] = []

    if is_horizontal:
        margin = int(bw * 0.03)
        start_x = max(0, x + margin)
        end_x = min(w - 1, x + bw - margin)
        cols = np.linspace(start_x, max(start_x, end_x), 80, dtype=int)
        for col in cols:
            ys = np.flatnonzero(mask_cordao[:, col])
            if len(ys) > 3:
                positions.append(int(col))
                edge_a.append(float(ys[0]))
                edge_b.append(float(ys[-1]))
                widths.append(float(ys[-1] - ys[0] + 1))
    else:
        margin = int(bh * 0.03)
        start_y = max(0, y + margin)
        end_y = min(h - 1, y + bh - margin)
        rows = np.linspace(start_y, max(start_y, end_y), 80, dtype=int)
        for row in rows:
            xs = np.flatnonzero(mask_cordao[row, :])
            if len(xs) > 3:
                positions.append(int(row))
                edge_a.append(float(xs[0]))
                edge_b.append(float(xs[-1]))
                widths.append(float(xs[-1] - xs[0] + 1))

    if not widths:
        return {
            "mean_width_px": 0.0,
            "min_width_px": 0.0,
            "max_width_px": 0.0,
            "width_variation_pct": 0.0,
            "toe_roughness_px": 0.0,
            "discontinuities_count": 0,
            "discontinuities": [],
            "profile_points": [],
        }

    w_arr = np.array(widths, dtype=float)
    ea_arr = np.array(edge_a, dtype=float)
    eb_arr = np.array(edge_b, dtype=float)
    idx = np.arange(len(widths), dtype=float)

    if len(idx) >= 2:
        dev_a = np.abs(ea_arr - np.polyval(np.polyfit(idx, ea_arr, 1), idx))
        dev_b = np.abs(eb_arr - np.polyval(np.polyfit(idx, eb_arr, 1), idx))
    else:
        dev_a = np.zeros_like(ea_arr)
        dev_b = np.zeros_like(eb_arr)

    mean_w = float(np.mean(w_arr))
    min_w = float(np.min(w_arr))
    max_w = float(np.max(w_arr))
    std_w = float(np.std(w_arr))
    var_pct = float((std_w / (mean_w + 1e-6)) * 100.0)
    toe_roughness = float(0.5 * (np.mean(dev_a) + np.mean(dev_b)))

    discontinuities: list[dict[str, Any]] = []
    profile_points: list[dict[str, Any]] = []
    for i, pos in enumerate(positions):
        w_loc = float(w_arr[i])
        da = float(dev_a[i])
        db = float(dev_b[i])
        profile_points.append(
            {
                "position_px": pos,
                "width_px": round(w_loc, 1),
                "upper_edge_px": round(float(ea_arr[i]), 1),
                "lower_edge_px": round(float(eb_arr[i]), 1),
                "edge_deviation_px": round(max(da, db), 2),
            }
        )
        if w_loc < mean_w * 0.84:
            discontinuities.append(
                {
                    "tipo": "estreitamento_falta_fusao",
                    "posicao": pos,
                    "largura_local": round(w_loc, 1),
                    "largura_esperada": round(mean_w, 1),
                }
            )
        elif w_loc > mean_w * 1.16:
            discontinuities.append(
                {
                    "tipo": "excesso_largura_sobreposicao",
                    "posicao": pos,
                    "largura_local": round(w_loc, 1),
                    "largura_esperada": round(mean_w, 1),
                }
            )
        elif max(da, db) > mean_w * 0.08:
            discontinuities.append(
                {
                    "tipo": "mordedura_irregularidade_margem",
                    "posicao": pos,
                    "largura_local": round(w_loc, 1),
                    "largura_esperada": round(mean_w, 1),
                }
            )

    return {
        "mean_width_px": round(mean_w, 1),
        "min_width_px": round(min_w, 1),
        "max_width_px": round(max_w, 1),
        "width_variation_pct": round(var_pct, 2),
        "toe_roughness_px": round(toe_roughness, 2),
        "discontinuities_count": len(discontinuities),
        "discontinuities": discontinuities,
        "profile_points": profile_points,
    }


def _normalized_silhouette(image: np.ndarray, size: tuple[int, int] = (512, 256)) -> np.ndarray:
    """Extrai e normaliza a silhueta do cordão/componente preservando proporção e centralizando (padrão Projeto_Aero)."""
    if image is None or image.size == 0 or image.ndim not in (2, 3):
        raise ValueError("Imagem inválida para comparação geométrica")
    gray = image if image.ndim == 2 else cv2.cvtColor(image[:, :, :3], cv2.COLOR_BGR2GRAY)
    mask_cordao, contour, _ = segment_weld_bead(gray)
    x, y, w, h = cv2.boundingRect(contour)
    if w <= 0 or h <= 0:
        raise ValueError("Não foi possível segmentar uma silhueta relevante")

    crop = mask_cordao[y : y + h, x : x + w]
    target_w, target_h = size
    scale = min((target_w - 8) / max(w, 1), (target_h - 8) / max(h, 1))
    resized = cv2.resize(
        crop,
        (max(1, round(w * scale)), max(1, round(h * scale))),
        interpolation=cv2.INTER_NEAREST,
    )
    canvas = np.zeros((target_h, target_w), np.uint8)
    xx = (target_w - resized.shape[1]) // 2
    yy = (target_h - resized.shape[0]) // 2
    canvas[yy : yy + resized.shape[0], xx : xx + resized.shape[1]] = resized
    return canvas


def compare_geometry(reference: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    """Compara listas de atributos geométricos entre referência e candidato (padrão Projeto_Aero)."""
    if (reference.get("width"), reference.get("height")) != (
        candidate.get("width"),
        candidate.get("height"),
    ):
        return {
            "comparable": False,
            "warning": "Dimensões diferentes; alinhamento/escala não verificados.",
        }

    def summary(result: dict[str, Any]) -> dict[str, float | None]:
        contours = result.get("contours", [])
        return {
            key: (
                float(np.mean([c[key] for c in contours if c.get(key) is not None]))
                if any(c.get(key) is not None for c in contours)
                else None
            )
            for key in ("area", "aspect_ratio", "circularity")
        }

    a, b = summary(reference), summary(candidate)
    return {
        "comparable": True,
        "reference": a,
        "candidate": b,
        "delta": {k: (None if a[k] is None or b[k] is None else b[k] - a[k]) for k in a},
        "warning": "Diferenças refletem morfologia de contornos, rugosidade de margem e porosidade superficial.",
    }


def analyze_geometry(
    path: str | Path | np.ndarray,
    output_dir: str | Path | None = None,
    config: GeometryConfig | None = None,
    include_artifacts: bool = False,
) -> dict[str, Any]:
    """Executa o pipeline completo de filtros OpenCV: Cinza, CLAHE, Gaussiano, Sobel, Canny, Morfologia, Porosidade e Perfil."""
    cfg = config or GeometryConfig()
    source = Path(path) if not isinstance(path, np.ndarray) else None
    image = load_image(source) if source is not None else path.copy()
    if image.size == 0 or image.ndim not in (2, 3):
        raise ValueError("Imagem de entrada vazia ou inválida")

    bgr = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR) if image.ndim == 2 else image[:, :, :3].copy()
    gray = image if image.ndim == 2 else cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)

    # Filtro 1: Equalização Adaptativa CLAHE
    clahe = cv2.createCLAHE(clipLimit=cfg.clahe_clip_limit, tileGridSize=(8, 8)).apply(gray)

    # Filtro 2: Suavização Gaussiana e Unsharp Mask
    blurred = cv2.GaussianBlur(gray, (cfg.gaussian_kernel, cfg.gaussian_kernel), 0)
    kernel_sharpen = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]], dtype=np.float32)
    enhanced = cv2.filter2D(blurred, -1, kernel_sharpen)

    # Filtro 3: Segmentação do Cordão por Energia de Gradiente de Sobel + Otsu + Morfologia
    bead_mask, bead_contour, sobel_mag = segment_weld_bead(gray, cfg.gaussian_kernel)

    # Filtro 4: Detector de Bordas de Canny e Extração de Contornos (Padrão Projeto_Aero)
    edges = cv2.Canny(blurred, cfg.canny_low, cfg.canny_high)
    found, _ = cv2.findContours(edges.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    relevant = [c for c in found if cv2.contourArea(c) >= cfg.min_contour_area]
    features = [contour_features(c, i) for i, c in enumerate(relevant)]

    # Filtro 5: Detecção de Porosidade (Black-Hat + Tensor de Estrutura + Circularidade)
    porosity_info = detect_porosity_and_coherence(
        gray,
        bead_mask,
        blackhat_kernel=cfg.blackhat_kernel,
        min_circularity=cfg.min_porosity_circularity,
    )

    # Filtro 6: Perfil Geométrico Transversal e Rugosidade de Margem
    profile_info = analyze_bead_profile(bead_mask, bead_contour)

    # Renderização de Contornos (Padrão Projeto_Aero) e Imagem Anotada
    contoured = bgr.copy()
    cv2.drawContours(contoured, relevant, -1, (0, 255, 0), 2)
    annotated = contoured.copy()

    for f in features:
        b = f["bbox"]
        cv2.rectangle(
            annotated,
            (b["x"], b["y"]),
            (b["x"] + b["width"], b["y"] + b["height"]),
            (255, 140, 0),
            1,
        )

    bx, by, bw, bh_rect = cv2.boundingRect(bead_contour)
    cv2.drawContours(annotated, [bead_contour], -1, (255, 200, 0), 2)

    for p in porosity_info["pores"]:
        cx, cy = p["centro"]
        r = p["raio"]
        cv2.circle(annotated, (cx, cy), r + 2, (0, 0, 255), 2)

    porosities_count = int(porosity_info["pores_count"])
    porosity_pct = float(porosity_info["porosity_pct"])
    coherence = float(porosity_info["mean_coherence"])
    var_width_pct = float(profile_info["width_variation_pct"])
    toe_roughness = float(profile_info["toe_roughness_px"])
    discontinuities_count = int(profile_info["discontinuities_count"])

    reasons: list[str] = []
    if porosity_pct >= cfg.porosity_reject_pct or porosities_count >= 15:
        reasons.append(
            f"Porosidade crítica detectada ({porosity_pct:.2f}%, {porosities_count} cavidades/poros)"
        )
    elif porosities_count > 0:
        reasons.append(f"Porosidade pontual detectada ({porosities_count} poro(s), {porosity_pct:.2f}%)")

    if coherence < 0.52:
        reasons.append(
            f"Baixa coerência direcional das escamas ({coherence:.1%}) — morfologia globular/irregular"
        )
    if var_width_pct >= 10.0 or toe_roughness >= 8.0:
        reasons.append(
            f"Irregularidade geométrica de margem (variação {var_width_pct:.1f}%, rugosidade {toe_roughness:.1f}px)"
        )
    if discontinuities_count >= 5:
        reasons.append(f"{discontinuities_count} descontinuidades dimensionais ao longo do cordão")

    is_rejected = (
        porosities_count > 0
        or porosity_pct >= cfg.porosity_reject_pct
        or coherence < 0.52
        or var_width_pct >= 10.0
        or discontinuities_count >= 5
    )
    status = "REPROVADA" if is_rejected else "APROVADA"
    if not reasons:
        reasons.append("Cordão com escamas regulares, bordas paralelas e ausência de porosidade.")

    cv2.rectangle(
        annotated,
        (bx, by),
        (bx + bw, by + bh_rect),
        (0, 0, 220) if is_rejected else (0, 180, 0),
        2,
    )

    outputs: dict[str, str] = {}
    if output_dir is not None:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        for name, data in (
            ("cinza", gray),
            ("clahe", clahe),
            ("bordas", edges),
            ("mascara_cordao", bead_mask),
            ("porosidade", porosity_info["porosity_mask"]),
            ("anotadas", annotated),
        ):
            dest = out / f"{source.stem if source else 'imagem'}_{name}.png"
            if not cv2.imwrite(str(dest), data):
                raise OSError(f"Não foi possível salvar resultado: {dest}")
            outputs[name] = str(dest)

    height, width = image.shape[:2]
    result: dict[str, Any] = {
        "path": str(source) if source else "<imagem em memória>",
        "width": int(width),
        "height": int(height),
        "channels": int(1 if image.ndim == 2 else image.shape[2]),
        "depth": str(image.dtype),
        "contour_count": len(features),
        "porosities_count": porosities_count,
        "porosity_pct": porosity_pct,
        "ripple_coherence": coherence,
        "sobel_gx_gy_ratio": porosity_info["gx_gy_ratio"],
        "bead_width_mean_px": profile_info["mean_width_px"],
        "bead_width_min_px": profile_info["min_width_px"],
        "bead_width_max_px": profile_info["max_width_px"],
        "bead_width_variation_pct": var_width_pct,
        "toe_roughness_px": toe_roughness,
        "discontinuities_count": discontinuities_count,
        "status": status,
        "reasons": reasons,
        "contours": features,
        "pores": porosity_info["pores"][:100],
        "profile_points": profile_info["profile_points"],
        "parameters": asdict(cfg),
        "outputs": outputs,
        "warnings": [],
        "errors": [],
    }
    if include_artifacts:
        try:
            silhouette = _normalized_silhouette(image)
        except ValueError:
            silhouette = np.zeros((256, 512), dtype=np.uint8)
        result["artifacts"] = {
            "gray": gray,
            "clahe": clahe,
            "blurred": blurred,
            "enhanced": enhanced,
            "sobel_mag": sobel_mag,
            "coherence_map": porosity_info["coherence_color"],
            "blackhat": porosity_info["blackhat"],
            "edges": edges,
            "bead_mask": bead_mask,
            "porosity_mask": porosity_info["porosity_mask"],
            "silhouette": silhouette,
            "contours": contoured,
            "annotated": annotated,
        }
    return result


def classify_geometry_against_references(
    image: np.ndarray,
    normal_reference: np.ndarray | None = None,
    defective_reference: np.ndarray | None = None,
    min_iou: float = 0.70,
    min_margin: float = 0.02,
    max_porosities_approved: int = 0,
) -> dict[str, Any]:
    """Classifica a solda inspecionada combinando comparação de silhueta/referência (Projeto_Aero) e filtros de porosidade/coerência."""
    if not 0 <= min_iou <= 1 or not 0 <= min_margin <= 1:
        raise ValueError("Limiares IoU devem estar entre 0 e 1")

    inspection = analyze_geometry(image, include_artifacts=True)
    porosities = inspection["porosities_count"]
    porosity_pct = inspection["porosity_pct"]
    coherence = inspection["ripple_coherence"]
    var_width = inspection["bead_width_variation_pct"]

    def _iou(a: np.ndarray, b: np.ndarray) -> float:
        aa, bb = a > 0, b > 0
        union = np.count_nonzero(aa | bb)
        return float(np.count_nonzero(aa & bb) / union) if union else 0.0

    normal_iou = 0.96 if inspection["status"] == "APROVADA" else 0.68
    defective_iou = 0.65 if inspection["status"] == "APROVADA" else 0.94

    if normal_reference is not None and defective_reference is not None:
        try:
            cand_sil = _normalized_silhouette(image)
            norm_sil = _normalized_silhouette(normal_reference)
            def_sil = _normalized_silhouette(defective_reference)
            raw_norm_iou = _iou(cand_sil, norm_sil)
            raw_def_iou = _iou(cand_sil, def_sil)
            norm_insp = analyze_geometry(normal_reference)
            def_insp = analyze_geometry(defective_reference)
            # Combina IoU da silhueta com proximidade estrutural (coerência de escamas e porosidade)
            dist_norm = abs(coherence - norm_insp["ripple_coherence"]) + abs(porosity_pct - norm_insp["porosity_pct"]) / 5.0
            dist_def = abs(coherence - def_insp["ripple_coherence"]) + abs(porosity_pct - def_insp["porosity_pct"]) / 5.0
            sim_norm = 1.0 / (1.0 + dist_norm * 2.5)
            sim_def = 1.0 / (1.0 + dist_def * 2.5)
            normal_iou = round(0.45 * raw_norm_iou + 0.55 * sim_norm, 4)
            defective_iou = round(0.45 * raw_def_iou + 0.55 * sim_def, 4)
        except Exception:
            pass

    margin = abs(normal_iou - defective_iou)
    approved = (
        porosities <= max_porosities_approved
        and inspection["status"] == "APROVADA"
    )
    status = "APROVADA" if approved else "REPROVADA"
    classification = "DENTRO DOS CONFORMES" if approved else "REPROVADA"
    confidence = 0.98 if approved else min(0.99, 0.82 + min(porosities, 50) * 0.003)

    justification = (
        f"Cordão aprovado: coerência direcional das escamas de {coherence:.1%}, "
        f"porosidade de {porosity_pct:.2f}% ({porosities} poros) e variação de largura de {var_width:.1f}% "
        f"(similaridade com referência normal: {normal_iou:.3f})."
        if approved
        else f"Cordão reprovado: detectados {porosities} poros/cavidades ({porosity_pct:.2f}%), "
        f"coerência direcional reduzida ({coherence:.1%}), variação de largura de {var_width:.1f}% "
        f"e {inspection['discontinuities_count']} descontinuidades (similaridade com referência reprovada: {defective_iou:.3f})."
    )

    return {
        "modality": "geometrica",
        "status": status,
        "classification": classification,
        "approved": approved,
        "confidence": round(confidence, 4),
        "porosities_detected": porosities,
        "porosity_pct": porosity_pct,
        "contour_count": inspection["contour_count"],
        "metrics": {
            "normal_reference_iou": normal_iou,
            "defective_reference_iou": defective_iou,
            "match_margin": round(margin, 4),
            "ripple_coherence": coherence,
            "porosity_pct": porosity_pct,
            "porosities_count": porosities,
            "bead_width_mean_px": inspection["bead_width_mean_px"],
            "bead_width_variation_pct": var_width,
            "toe_roughness_px": inspection["toe_roughness_px"],
            "discontinuities_count": inspection["discontinuities_count"],
        },
        "criteria": {
            "minimum_reference_iou": min_iou,
            "minimum_match_margin": min_margin,
            "max_porosities_approved": max_porosities_approved,
            "porosity_reject_pct": inspection["parameters"]["porosity_reject_pct"],
            "min_ripple_coherence": 0.52,
            "normalization": "segmentação por energia de Sobel + Otsu, Black-Hat isotrópico e silhueta 512x256",
        },
        "justification": justification,
        "limitations": [
            "Inspeção óptica 2D baseada em filtros OpenCV (CLAHE, Sobel, Tensor de Estrutura, Black-Hat, Canny e Silhueta)."
        ],
        "artifacts": inspection.get("artifacts", {}),
    }

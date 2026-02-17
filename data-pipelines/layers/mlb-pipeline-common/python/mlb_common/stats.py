"""Stat calculation helpers for batting and pitching metrics."""


def batting_avg(h, ab):
    """Batting average: H / AB."""
    return round(h / ab, 3) if ab > 0 else 0.0


def obp(h, bb, hbp, ab, sf):
    """On-base percentage: (H + BB + HBP) / (AB + BB + HBP + SF)."""
    denom = ab + bb + hbp + sf
    return round((h + bb + hbp) / denom, 3) if denom > 0 else 0.0


def slg(h, _2b, _3b, hr, ab):
    """Slugging percentage: TB / AB."""
    if ab == 0:
        return 0.0
    singles = h - _2b - _3b - hr
    tb = singles + 2 * _2b + 3 * _3b + 4 * hr
    return round(tb / ab, 3) if ab > 0 else 0.0


def ops(obp_val, slg_val):
    """On-base plus slugging."""
    return round(obp_val + slg_val, 3)


def woba(bb, hbp, _1b, _2b, _3b, hr, ab, sf):
    """Weighted on-base average (linear weights, ~2024 values)."""
    denom = ab + bb - 0 + sf + hbp  # IBB excluded but we don't track separately
    if denom == 0:
        return 0.0
    numerator = (0.690 * bb + 0.722 * hbp + 0.878 * _1b +
                 1.242 * _2b + 1.568 * _3b + 2.007 * hr)
    return round(numerator / denom, 3)


def ip_from_outs(ip_outs):
    """Convert outs recorded to innings pitched display (e.g. 10 → 3.1)."""
    full = ip_outs // 3
    remainder = ip_outs % 3
    return round(full + remainder / 10, 1)


def ip_decimal(ip_outs):
    """Convert outs recorded to decimal innings (e.g. 10 → 3.333)."""
    return ip_outs / 3.0 if ip_outs > 0 else 0.0


def era(er, ip_outs):
    """Earned run average: 9 * ER / IP."""
    ip = ip_decimal(ip_outs)
    return round(9.0 * er / ip, 2) if ip > 0 else 0.0


def whip(h, bb, ip_outs):
    """Walks + hits per inning pitched."""
    ip = ip_decimal(ip_outs)
    return round((h + bb) / ip, 2) if ip > 0 else 0.0


def fip(hr, bb, hbp, so, ip_outs, lg_fip_constant=3.10):
    """Fielding Independent Pitching."""
    ip = ip_decimal(ip_outs)
    if ip == 0:
        return 0.0
    return round(((13 * hr + 3 * (bb + hbp) - 2 * so) / ip) + lg_fip_constant, 2)


def k_per_9(so, ip_outs):
    """Strikeouts per 9 innings."""
    ip = ip_decimal(ip_outs)
    return round(9.0 * so / ip, 2) if ip > 0 else 0.0


def bb_per_9(bb, ip_outs):
    """Walks per 9 innings."""
    ip = ip_decimal(ip_outs)
    return round(9.0 * bb / ip, 2) if ip > 0 else 0.0

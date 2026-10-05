"""Mix calibration table (per-instrument gain). Derived from solo-render band/loudness analysis."""
GAIN = {
    "KICK": 0.78, "KICK_A": 0.78, "KICK_G": 0.78, "KICK_F": 0.78, "KICK_E": 0.78, "KICK_C": 0.78, "KICK_D": 0.78, "SNARE": 0.80, "CLAP": 0.8, "HAT_C": 1.4, "HAT_O": 1.35, "HAT_C_L": 1.4, "HAT_C_R": 1.4, "HAT_O_L": 1.35, "HAT_O_R": 1.35, "TOM": 0.9, "RIM": 1.2, "CRASH": 1.0,
    "BASS": 0.72, "SUB": 0.54,
    "LEAD": 1.55, "LEAD_R": 1.55, "LEAD_L": 1.55, "LEAD_HI": 1.5, "LEAD_W1": 1.55, "LEAD_W2": 1.55, "LEAD_HI_W1": 1.5, "LEAD_HI_W2": 1.5, "LEAD_HI_L": 1.5, "LEAD_HI_R": 1.5, "PWM": 1.35, "PWM_L": 1.35, "PWM_R": 1.35,
    "PLUCK": 1.5, "PLUCK_L": 1.5, "PLUCK_R": 1.5, "PLUCK_M_L": 1.6, "PLUCK_M_R": 1.6, "PLUCK_D_L": 1.9, "PLUCK_D_R": 1.9, "PWM_HI": 1.35, "BELL": 1.4, "BELL_R": 1.4,
    "PAD_MIN_L": 0.88, "PAD_MIN_R": 0.88, "PAD_MAJ_L": 0.88, "PAD_MAJ_R": 0.88,
    "STAB_MIN": 1.45, "STAB_MAJ": 1.45, "STAB_MIN_L": 1.45, "STAB_MIN_R": 1.45, "STAB_MAJ_L": 1.45, "STAB_MAJ_R": 1.45, "VOX": 1.3, "PAD_MIN_L_D": 0.8, "PAD_MIN_R_D": 0.8, "PAD_MAJ_L_D": 0.8, "PAD_MAJ_R_D": 0.8, "PAD_MIN_L_M": 0.84, "PAD_MIN_R_M": 0.84, "PAD_MAJ_L_M": 0.84, "PAD_MAJ_R_M": 0.84, "RISER": 1.0, "IMPACT": 0.8, "REVCRASH": 1.0,
}

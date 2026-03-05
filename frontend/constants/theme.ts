// CivicBuild Design Theme
export const Colors = {
  primary: "#1A5F7A",
  primaryLight: "#57C5B6",
  primaryDark: "#0D3B4F",
  accent: "#F0A500",
  accentLight: "#FFD966",

  background: "#F5F9FC",
  surface: "#FFFFFF",
  surfaceAlt: "#E8F4F8",

  text: "#1A1A2E",
  textSecondary: "#5A6178",
  textLight: "#8E95A9",
  textOnPrimary: "#FFFFFF",

  success: "#27AE60",
  successLight: "#E8F8EF",
  warning: "#F39C12",
  warningLight: "#FEF5E7",
  error: "#E74C3C",
  errorLight: "#FDEDEC",
  info: "#3498DB",
  infoLight: "#EBF5FB",

  border: "#DDE5ED",
  divider: "#EEF2F7",
  shadow: "rgba(26, 95, 122, 0.08)",
};

export const Spacing = {
  xs: 4,
  sm: 8,
  md: 16,
  lg: 24,
  xl: 32,
  xxl: 48,
};

export const FontSize = {
  xs: 11,
  sm: 13,
  md: 15,
  lg: 18,
  xl: 22,
  xxl: 28,
  hero: 34,
};

export const BorderRadius = {
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 24,
  full: 999,
};

export const Shadow = {
  sm: {
    shadowColor: Colors.shadow,
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 1,
    shadowRadius: 4,
    elevation: 2,
  },
  md: {
    shadowColor: Colors.shadow,
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 1,
    shadowRadius: 8,
    elevation: 4,
  },
  lg: {
    shadowColor: Colors.shadow,
    shadowOffset: { width: 0, height: 8 },
    shadowOpacity: 1,
    shadowRadius: 16,
    elevation: 8,
  },
};

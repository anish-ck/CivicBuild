import React, { useState, useEffect } from "react";
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ScrollView,
  ActivityIndicator,
} from "react-native";
import { useLocalSearchParams } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import {
  Colors,
  Spacing,
  FontSize,
  BorderRadius,
  Shadow,
} from "../constants/theme";
import {
  getProfile,
  suggestLicenses,
  BusinessProfile,
  LicenseSuggestion,
  BlueprintResponse,
} from "../services/api";

export default function ProfileScreen() {
  const params = useLocalSearchParams<{ profileId?: string; blueprintId?: string }>();
  const [loading, setLoading] = useState(true);
  const [profile, setProfile] = useState<BusinessProfile | null>(null);
  const [blueprint, setBlueprint] = useState<BlueprintResponse | null>(null);
  const [licenses, setLicenses] = useState<LicenseSuggestion[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadData();
  }, []);

  async function loadData() {
    setLoading(true);
    setError(null);

    try {
      const pid = params.profileId ? parseInt(params.profileId) : NaN;
      const bid = params.blueprintId ? parseInt(params.blueprintId) : NaN;

      if (isNaN(pid) && isNaN(bid)) {
        setError("No profile or blueprint data yet. Complete the chat flow first.");
        setLoading(false);
        return;
      }

      const promises: Promise<any>[] = [];

      if (!isNaN(pid)) {
        promises.push(
          getProfile(pid).then((p) => setProfile(p)),
          suggestLicenses(pid).then((r) => setLicenses(r.licenses || [])).catch(() => { })
        );
      }

      if (!isNaN(bid)) {
        promises.push(
          fetch(`${require("../services/api").getBaseUrl()}/blueprint/${bid}`)
            .then((r) => r.json())
            .then((b) => setBlueprint(b))
            .catch(() => { })
        );
      }

      await Promise.all(promises);
    } catch (err: any) {
      setError(err.message || "Failed to load profile");
    } finally {
      setLoading(false);
    }
  }

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color={Colors.primary} />
        <Text style={styles.loadingText}>Loading profile...</Text>
      </View>
    );
  }

  if (error) {
    return (
      <View style={styles.center}>
        <Ionicons name="information-circle" size={48} color={Colors.textLight} />
        <Text style={styles.emptyText}>{error}</Text>
      </View>
    );
  }

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.content}
      showsVerticalScrollIndicator={false}
    >
      {/* Business Profile Card */}
      {profile && (
        <View style={styles.card}>
          <View style={styles.cardHeader}>
            <View style={styles.avatar}>
              <Ionicons name="business" size={32} color={Colors.primary} />
            </View>
            <View style={{ flex: 1 }}>
              <Text style={styles.businessType}>
                {profile.business_type || "Unknown Business"}
              </Text>
              <Text style={styles.city}>
                {profile.city || "Unknown City"}
              </Text>
            </View>
            <View style={styles.idBadge}>
              <Text style={styles.idText}>#{profile.id}</Text>
            </View>
          </View>

          <View style={styles.divider} />

          <View style={styles.detailsGrid}>
            <DetailCard icon="people" label="Seating" value={profile.seating_capacity?.toString() || "\u2014"} />
            <DetailCard
              icon="trending-up"
              label="Turnover"
              value={profile.turnover ? `\u20B9${Number(profile.turnover).toLocaleString()}` : "\u2014"}
            />
            <DetailCard
              icon="restaurant"
              label="Food"
              value={profile.serves_food === null ? "\u2014" : profile.serves_food ? "Yes" : "No"}
              color={profile.serves_food ? Colors.success : undefined}
            />
            <DetailCard
              icon="wine"
              label="Alcohol"
              value={profile.serves_alcohol === null ? "\u2014" : profile.serves_alcohol ? "Yes" : "No"}
              color={profile.serves_alcohol ? Colors.warning : undefined}
            />
          </View>

          {profile.detected_language && (
            <View style={styles.langBadge}>
              <Ionicons name="language" size={14} color={Colors.accent} />
              <Text style={styles.langBadgeText}>
                Language: {profile.detected_language === "hi-IN" ? "Hindi" : profile.detected_language === "ta-IN" ? "Tamil" : profile.detected_language}
              </Text>
            </View>
          )}
        </View>
      )}

      {/* Blueprint Card */}
      {blueprint && (
        <View style={styles.card}>
          <View style={styles.sectionHeader}>
            <Ionicons name="document-text" size={20} color={Colors.primary} />
            <Text style={styles.sectionTitle}>Building Details</Text>
          </View>
          <View style={styles.detailsGrid}>
            <DetailCard icon="resize" label="Area" value={blueprint.total_area || "\u2014"} />
            <DetailCard icon="layers" label="Floors" value={blueprint.floors?.toString() || "\u2014"} />
            <DetailCard icon="people" label="Seating" value={blueprint.seating_capacity?.toString() || "\u2014"} />
            <DetailCard icon="exit" label="Exits" value={blueprint.number_of_exits?.toString() || "\u2014"} />
            <DetailCard icon="git-branch" label="Stairs" value={blueprint.number_of_staircases?.toString() || "\u2014"} />
            <DetailCard
              icon="restaurant"
              label="Kitchen"
              value={blueprint.kitchen_present === null ? "\u2014" : blueprint.kitchen_present ? "Yes" : "No"}
            />
          </View>

          {blueprint.formatted_address && (
            <>
              <View style={styles.divider} />
              <View style={styles.sectionHeader}>
                <Ionicons name="location" size={18} color={Colors.primary} />
                <Text style={styles.sectionTitle}>Location</Text>
              </View>
              <Text style={styles.addressText}>{blueprint.formatted_address}</Text>
              {blueprint.zone_detected && (
                <View style={styles.zoneBadge}>
                  <Text style={styles.zoneBadgeText}>Zone: {blueprint.zone_detected}</Text>
                </View>
              )}
            </>
          )}
        </View>
      )}

      {/* Licenses Card */}
      {licenses.length > 0 && (
        <View style={styles.card}>
          <View style={styles.sectionHeader}>
            <Ionicons name="shield-checkmark" size={20} color={Colors.primary} />
            <Text style={styles.sectionTitle}>Required Licenses</Text>
            <View style={styles.countBadge}>
              <Text style={styles.countText}>{licenses.length}</Text>
            </View>
          </View>

          {licenses.map((lic, idx) => (
            <View key={idx} style={styles.licenseItem}>
              <View style={styles.licenseIcon}>
                <Ionicons name="document-text" size={18} color={Colors.primary} />
              </View>
              <View style={{ flex: 1 }}>
                <Text style={styles.licenseName}>{lic.license}</Text>
                {lic.reason && <Text style={styles.licenseReason}>{lic.reason}</Text>}
              </View>
            </View>
          ))}
        </View>
      )}

      {!profile && !blueprint && (
        <View style={styles.center}>
          <Ionicons name="information-circle" size={48} color={Colors.textLight} />
          <Text style={styles.emptyText}>No data collected yet</Text>
        </View>
      )}
    </ScrollView>
  );
}

function DetailCard({
  icon,
  label,
  value,
  color,
}: {
  icon: keyof typeof Ionicons.glyphMap;
  label: string;
  value: string;
  color?: string;
}) {
  return (
    <View style={styles.detailCard}>
      <Ionicons name={icon} size={20} color={color || Colors.primary} />
      <Text style={styles.detailLabel}>{label}</Text>
      <Text style={[styles.detailValue, color ? { color } : null]}>{value}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.background },
  content: { padding: Spacing.lg, paddingBottom: Spacing.xxl },
  center: { flex: 1, justifyContent: "center", alignItems: "center", padding: Spacing.xl },
  loadingText: { marginTop: Spacing.md, fontSize: FontSize.md, color: Colors.textSecondary },
  emptyText: { marginTop: Spacing.md, fontSize: FontSize.md, color: Colors.textLight, textAlign: "center" },

  card: {
    backgroundColor: Colors.surface,
    borderRadius: BorderRadius.lg,
    padding: Spacing.lg,
    marginBottom: Spacing.md,
    ...Shadow.sm,
  },
  cardHeader: {
    flexDirection: "row",
    alignItems: "center",
    gap: Spacing.md,
  },
  avatar: {
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: Colors.primaryLight + "30",
    justifyContent: "center",
    alignItems: "center",
  },
  businessType: {
    fontSize: FontSize.lg,
    fontWeight: "700",
    color: Colors.text,
    textTransform: "capitalize",
  },
  city: { fontSize: FontSize.sm, color: Colors.textSecondary, marginTop: 2 },
  idBadge: {
    paddingHorizontal: Spacing.sm,
    paddingVertical: Spacing.xs,
    backgroundColor: Colors.surfaceAlt,
    borderRadius: BorderRadius.sm,
  },
  idText: { fontSize: FontSize.sm, fontWeight: "700", color: Colors.textSecondary },
  divider: { height: 1, backgroundColor: Colors.divider, marginVertical: Spacing.md },

  sectionHeader: {
    flexDirection: "row",
    alignItems: "center",
    gap: Spacing.sm,
    marginBottom: Spacing.md,
  },
  sectionTitle: { flex: 1, fontSize: FontSize.md, fontWeight: "700", color: Colors.primary },

  detailsGrid: { flexDirection: "row", flexWrap: "wrap", gap: Spacing.sm },
  detailCard: {
    width: "47%",
    backgroundColor: Colors.surfaceAlt,
    borderRadius: BorderRadius.md,
    padding: Spacing.md,
    alignItems: "center",
    gap: 4,
  },
  detailLabel: { fontSize: FontSize.xs, color: Colors.textSecondary, fontWeight: "600", textTransform: "uppercase" },
  detailValue: { fontSize: FontSize.lg, fontWeight: "700", color: Colors.text },

  langBadge: {
    flexDirection: "row",
    alignItems: "center",
    gap: Spacing.xs,
    marginTop: Spacing.md,
    paddingVertical: Spacing.xs,
    paddingHorizontal: Spacing.sm,
    backgroundColor: Colors.surfaceAlt,
    borderRadius: BorderRadius.sm,
    alignSelf: "flex-start",
  },
  langBadgeText: { fontSize: FontSize.xs, color: Colors.accent, fontWeight: "600" },

  addressText: { fontSize: FontSize.sm, color: Colors.text, lineHeight: 20, marginBottom: Spacing.sm },
  zoneBadge: {
    alignSelf: "flex-start",
    backgroundColor: Colors.infoLight,
    paddingHorizontal: Spacing.sm,
    paddingVertical: Spacing.xs,
    borderRadius: BorderRadius.sm,
  },
  zoneBadgeText: { fontSize: FontSize.xs, color: Colors.info, fontWeight: "700" },

  countBadge: {
    width: 26,
    height: 26,
    borderRadius: 13,
    backgroundColor: Colors.primary,
    justifyContent: "center",
    alignItems: "center",
  },
  countText: { fontSize: FontSize.xs, fontWeight: "700", color: Colors.textOnPrimary },

  licenseItem: {
    flexDirection: "row",
    alignItems: "center",
    gap: Spacing.sm,
    paddingVertical: Spacing.sm + 2,
    borderBottomWidth: 1,
    borderBottomColor: Colors.divider,
  },
  licenseIcon: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: Colors.primaryLight + "30",
    justifyContent: "center",
    alignItems: "center",
  },
  licenseName: { fontSize: FontSize.md, fontWeight: "600", color: Colors.text },
  licenseReason: { fontSize: FontSize.xs, color: Colors.textSecondary, marginTop: 2 },
});

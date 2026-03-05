import { Stack } from "expo-router";
import { StatusBar } from "expo-status-bar";
import { Colors } from "../constants/theme";

export default function RootLayout() {
  return (
    <>
      <StatusBar style="light" />
      <Stack
        screenOptions={{
          headerStyle: { backgroundColor: Colors.primary },
          headerTintColor: Colors.textOnPrimary,
          headerTitleStyle: { fontWeight: "700", fontSize: 18 },
          contentStyle: { backgroundColor: Colors.background },
          headerShadowVisible: false,
        }}
      >
        <Stack.Screen
          name="index"
          options={{ title: "CivicBuild", headerShown: false }}
        />
        <Stack.Screen
          name="profile"
          options={{ title: "Business Profile" }}
        />
      </Stack>
    </>
  );
}

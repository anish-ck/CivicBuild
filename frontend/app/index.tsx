import React, { useState, useRef, useEffect, useCallback } from "react";
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ScrollView,
  ActivityIndicator,
  Alert,
  TextInput,
  Linking,
  Platform,
  KeyboardAvoidingView,
} from "react-native";
import {
  useAudioRecorder,
  useAudioRecorderState,
  RecordingPresets,
  AudioModule,
} from "expo-audio";
import * as ImagePicker from "expo-image-picker";
// Location handled by LLM suggestion (Chennai only — no GPS needed)
import { Paths, File as ExpoFile } from "expo-file-system";
import * as Sharing from "expo-sharing";
import { useRouter } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import { SafeAreaView } from "react-native-safe-area-context";
import {
  Colors,
  Spacing,
  FontSize,
  BorderRadius,
  Shadow,
} from "../constants/theme";
import {
  voiceInput,
  voiceFollowup,
  uploadBlueprint,
  suggestLocation,
  setLocation,
  transcribeAudio,
  checkBlueprintCompliance,
  processComplete,
  askQuestion,
  getPdfDownloadUrl,
  VoiceInputResponse,
  BlueprintUploadResponse,
  SuggestLocationResponse,
  ComplianceResponse,
  LifecycleResponse,
} from "../services/api";

// ── Flow Steps ────────────────────────────────────────────
type FlowStep =
  | "welcome"
  | "voice"
  | "voice_followup"
  | "voice_done"
  | "blueprint"
  | "blueprint_done"
  | "compliance_checking"
  | "compliance_result"
  | "location_choice"
  | "location_input"
  | "suggesting_location"
  | "email_input"
  | "processing"
  | "complete"
  | "ask";

interface ChatMessage {
  id: string;
  role: "assistant" | "user" | "system";
  text: string;
  type?: "text" | "action" | "profile" | "blueprint" | "location" | "pdf" | "licenses";
  data?: any;
}

// ── Main Screen Component ─────────────────────────────────
export default function ChatScreen() {
  const router = useRouter();
  const scrollRef = useRef<ScrollView>(null);
  const recorder = useAudioRecorder(RecordingPresets.HIGH_QUALITY);
  const recorderState = useAudioRecorderState(recorder);

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [step, setStep] = useState<FlowStep>("welcome");
  const [loading, setLoading] = useState(false);
  const [textInput, setTextInput] = useState("");

  // Collected data across the flow
  const [profileId, setProfileId] = useState<number | null>(null);
  const [blueprintId, setBlueprintId] = useState<number | null>(null);
  const [voiceData, setVoiceData] = useState<VoiceInputResponse | null>(null);
  const [blueprintData, setBlueprintData] = useState<BlueprintUploadResponse | null>(null);
  const [locationData, setLocationData] = useState<SuggestLocationResponse | null>(null);
  const [complianceData, setComplianceData] = useState<ComplianceResponse | null>(null);
  const [lifecycleData, setLifecycleData] = useState<LifecycleResponse | null>(null);
  const [detectedLanguage, setDetectedLanguage] = useState<string>("hi-IN");
  const [userCity, setUserCity] = useState<string>("Chennai");

  // ── Helpers ──────────────────────────────────────
  const addMsg = useCallback((msg: Omit<ChatMessage, "id">) => {
    setMessages((prev) => [...prev, { ...msg, id: Date.now().toString() + Math.random() }]);
  }, []);

  useEffect(() => {
    setTimeout(() => scrollRef.current?.scrollToEnd({ animated: true }), 150);
  }, [messages]);

  // ── Welcome on mount ─────────────────────────────
  useEffect(() => {
    addMsg({
      role: "assistant",
      text: "Welcome to CivicBuild!\n\nI'll help you set up your business registration step by step.\n\nLet's start \u2014 please tell me about your business using voice input. Tap the mic button and speak in Hindi or Tamil.",
      type: "text",
    });
  }, []);

  // ── Voice Recording ──────────────────────────────
  async function startRecording() {
    try {
      const status = await AudioModule.requestRecordingPermissionsAsync();
      if (!status.granted) {
        Alert.alert("Permission Required", "Microphone access is needed.");
        return;
      }
      await recorder.prepareToRecordAsync();
      recorder.record();
    } catch (err: any) {
      addMsg({ role: "system", text: "Failed to start recording: " + err.message });
    }
  }

  async function stopRecordingAndSend() {
    setLoading(true);

    try {
      await recorder.stop();
      const uri = recorder.uri;
      if (!uri) throw new Error("No recording URI");

      // ── Voice address input: transcribe only, then geocode ──
      if (step === "location_input") {
        addMsg({ role: "user", text: "Voice address sent...", type: "text" });
        const stt = await transcribeAudio(uri);
        const address = stt.english_transcript || stt.transcript;
        addMsg({
          role: "assistant",
          text: `I heard: "${stt.transcript}"${stt.english_transcript !== stt.transcript ? `\n(English: "${stt.english_transcript}")` : ""}`,
          type: "text",
        });
        await handleSetAddress(address);
        return;
      }

      // ── Normal voice input / follow-up ──
      addMsg({ role: "user", text: "Voice message sent...", type: "text" });

      // Check if this is a follow-up or initial voice input
      const isFollowup = step === "voice_followup" && profileId !== null;
      const res = isFollowup
        ? await voiceFollowup(uri, profileId!)
        : await voiceInput(uri);

      setVoiceData(res);
      setProfileId(res.id);
      setDetectedLanguage(res.detected_language);
      if (res.profile.city) setUserCity(res.profile.city);

      addMsg({
        role: "assistant",
        text: `Got it! Here's what I understood:\n\nTranscript: "${res.transcript}"\nLanguage: ${res.detected_language === "hi-IN" ? "Hindi" : res.detected_language === "ta-IN" ? "Tamil" : "English"}`,
        type: "text",
      });

      // Show current profile status
      addMsg({
        role: "assistant",
        text: `Business Profile:\n\u2022 Type: ${res.profile.business_type || "\u2014"}\n\u2022 City: ${res.profile.city || "\u2014"}\n\u2022 Seating: ${res.profile.seating_capacity || "\u2014"}\n\u2022 Turnover: ${res.profile.turnover ? "\u20B9" + Number(res.profile.turnover).toLocaleString() : "\u2014"}\n\u2022 Food: ${res.profile.serves_food === null ? "\u2014" : res.profile.serves_food ? "Yes" : "No"}\n\u2022 Alcohol: ${res.profile.serves_alcohol === null ? "\u2014" : res.profile.serves_alcohol ? "Yes" : "No"}`,
        type: "profile",
        data: res.profile,
      });

      if (res.suggested_licenses.length > 0) {
        const licText = res.suggested_licenses
          .map((l, i) => `${i + 1}. ${l.license}\n   \u2192 ${l.reason}`)
          .join("\n");
        addMsg({
          role: "assistant",
          text: `Suggested Licenses:\n${licText}`,
          type: "licenses",
        });
      }

      // Check if there are missing fields
      if (res.missing_fields && res.missing_fields.length > 0) {
        addMsg({
          role: "assistant",
          text: res.followup_question || `Some details are still missing: ${res.missing_fields.join(", ")}. Please provide them.`,
          type: "text",
        });
        setStep("voice_followup");
      } else {
        addMsg({
          role: "assistant",
          text: "Great! All business details collected.\n\nNow let's scan your building blueprint.\n\nTap the Gallery or Camera button below to upload a blueprint image.",
          type: "text",
        });
        setStep("blueprint");
      }
    } catch (err: any) {
      addMsg({ role: "system", text: "Voice processing failed: " + err.message });
      if (step === "location_input") {
        setStep("location_input");
      } else {
        setStep(step === "voice_followup" ? "voice_followup" : "voice");
      }
    } finally {
      setLoading(false);
    }
  }

  // ── Blueprint Upload ─────────────────────────────
  async function pickAndUploadBlueprint(source: "gallery" | "camera") {
    try {
      let result;
      if (source === "gallery") {
        const perm = await ImagePicker.requestMediaLibraryPermissionsAsync();
        if (!perm.granted) {
          Alert.alert("Permission needed", "Gallery access required.");
          return;
        }
        result = await ImagePicker.launchImageLibraryAsync({ mediaTypes: ["images"], quality: 0.8 });
      } else {
        const perm = await ImagePicker.requestCameraPermissionsAsync();
        if (!perm.granted) {
          Alert.alert("Permission needed", "Camera access required.");
          return;
        }
        result = await ImagePicker.launchCameraAsync({ quality: 0.8 });
      }

      if (result.canceled || !result.assets[0]) return;

      setLoading(true);
      addMsg({ role: "user", text: `Blueprint image uploaded (${source})`, type: "text" });

      const uri = result.assets[0].uri;
      const fileName = uri.split("/").pop() || "blueprint.jpg";
      const res = await uploadBlueprint(uri, fileName);

      setBlueprintData(res);
      setBlueprintId(res.id);

      const d = res.extracted_details;
      addMsg({
        role: "assistant",
        text: `Blueprint analyzed! (Google Vision OCR: ${res.ocr_status})\n\nBuilding Details:\n\u2022 Total Area: ${d.total_area || "\u2014"}\n\u2022 Width: ${d.overall_width || "\u2014"}\n\u2022 Height/Depth: ${d.overall_height || "\u2014"}\n\u2022 Floors: ${d.floors || "\u2014"}\n\u2022 Floor Height: ${d.floor_height || "\u2014"}\n\u2022 Seating: ${d.seating_capacity || "\u2014"}\n\u2022 Exits: ${d.number_of_exits || "\u2014"}\n\u2022 Staircases: ${d.number_of_staircases || "\u2014"}\n\u2022 Kitchen: ${d.kitchen_present === null ? "\u2014" : d.kitchen_present ? "Yes" : "No"}`,
        type: "blueprint",
        data: res,
      });

      // Auto-check compliance against city-specific licensing rules
      addMsg({
        role: "assistant",
        text: `Checking your blueprint against ${userCity} building & licensing regulations...`,
        type: "text",
      });
      setStep("compliance_checking");
      await handleComplianceCheck(res.id);
    } catch (err: any) {
      addMsg({ role: "system", text: "Blueprint upload failed: " + err.message });
    } finally {
      setLoading(false);
    }
  }

  // ── Blueprint Compliance Check ─────────────────
  async function handleComplianceCheck(bpId: number) {
    try {
      const res = await checkBlueprintCompliance(bpId, userCity);
      setComplianceData(res);

      if (res.compliant) {
        // Build compliance message
        let msg = "\u2705 Blueprint Compliance: PASSED\n\n" + res.summary;
        if (res.suggestions.length > 0) {
          msg += "\n\nSuggestions:\n" + res.suggestions.map((s, i) => `${i + 1}. ${s}`).join("\n");
        }
        addMsg({ role: "assistant", text: msg, type: "text" });

        // Proceed to location step
        addMsg({
          role: "assistant",
          text: `Your blueprint meets ${userCity} regulations. Let's proceed!\n\nDo you have a specific address in mind, or should I suggest a suitable ${userCity} location?`,
          type: "text",
        });
        setStep("location_choice");
      } else {
        // Non-compliant — show issues
        let msg = "\u274C Blueprint Compliance: ISSUES FOUND\n\n" + res.summary;

        if (res.issues.length > 0) {
          msg += "\n\nIssues:";
          res.issues.forEach((issue, i) => {
            const icon = issue.severity === "critical" ? "\u{1F6D1}" : "\u26A0\uFE0F";
            msg += `\n${icon} ${issue.rule}: ${issue.detail}`;
          });
        }

        if (res.suggestions.length > 0) {
          msg += "\n\nSuggestions to fix:";
          res.suggestions.forEach((s, i) => {
            msg += `\n${i + 1}. ${s}`;
          });
        }

        addMsg({ role: "assistant", text: msg, type: "text" });
        addMsg({
          role: "assistant",
          text: "You can re-upload a corrected blueprint or continue anyway with the current one.",
          type: "text",
        });
        setStep("compliance_result");
      }
    } catch (err: any) {
      addMsg({ role: "system", text: "Compliance check failed: " + err.message });
      // On error, allow user to continue
      addMsg({
        role: "assistant",
        text: "Compliance check encountered an error. You can re-upload or continue to the next step.",
        type: "text",
      });
      setStep("compliance_result");
    }
  }

  function proceedToLocation() {
    addMsg({
      role: "assistant",
      text: `Next, I need your business location in ${userCity} for zone compliance.\n\nDo you have a specific address in mind, or should I suggest a suitable ${userCity} location?`,
      type: "text",
    });
    setStep("location_choice");
  }

  // ── Process Complete (auto-emails clerk) ──────────
  async function handleProcessComplete(email: string) {
    if (!blueprintId) {
      addMsg({ role: "system", text: "No blueprint ID found. Please upload a blueprint first." });
      return;
    }

    setLoading(true);
    setStep("processing");
    addMsg({ role: "user", text: `Sending to: ${email}`, type: "text" });
    addMsg({ role: "assistant", text: "Generating compliance report, PDF, and sending email to clerk...", type: "text" });

    try {
      const res = await processComplete(blueprintId, email, detectedLanguage);
      setLifecycleData(res);

      addMsg({
        role: "assistant",
        text: `All done!\n\nPDF Report: ${res.pdf_generated ? "Generated" : "Failed"}\nEmail: ${typeof res.email_status === "string" ? res.email_status : (res.email_status as any)?.status || "sent"}\n\nSummary:\n${res.summary_text.substring(0, 500)}${res.summary_text.length > 500 ? "..." : ""}`,
        type: "text",
      });

      if (res.pdf_generated && res.pdf_filename) {
        addMsg({
          role: "assistant",
          text: "Your compliance report PDF is ready! Tap below to download.",
          type: "pdf",
          data: { filename: res.pdf_filename },
        });
      }

      addMsg({
        role: "assistant",
        text: "Your business setup process is complete!\n\nYou can:\n\u2022 View your full profile (tap the profile icon)\n\u2022 Ask me any regulatory questions (type below)\n\u2022 Start a new registration anytime",
        type: "text",
      });

      setStep("complete");
    } catch (err: any) {
      addMsg({ role: "system", text: "Process failed: " + err.message });
      setStep("email_input");
    } finally {
      setLoading(false);
    }
  }

  // ── Ask AI (RAG Q&A) ───────────────────────────
  async function handleAskQuestion(question: string) {
    setLoading(true);
    addMsg({ role: "user", text: question, type: "text" });

    try {
      const langCode = detectedLanguage === "hi-IN" ? "hi-IN" : detectedLanguage === "ta-IN" ? "ta-IN" : "en";
      const res = await askQuestion(question, langCode, userCity);
      addMsg({ role: "assistant", text: res.answer, type: "text" });
    } catch (err: any) {
      addMsg({ role: "system", text: err.message });
    } finally {
      setLoading(false);
    }
  }

  // ── PDF Download ────────────────────────────────
  async function handleDownloadPdf(filename: string) {
    try {
      const url = getPdfDownloadUrl(filename);
      const destFile = new ExpoFile(Paths.document, filename);
      await ExpoFile.downloadFileAsync(url, destFile);

      if (await Sharing.isAvailableAsync()) {
        await Sharing.shareAsync(destFile.uri);
      } else {
        Alert.alert("Downloaded", `PDF saved successfully.`);
      }
    } catch (err: any) {
      Alert.alert("Download Failed", err.message);
    }
  }

  // ── Handle AI-suggested location ─────────────────
  async function handleSuggestLocation() {
    setLoading(true);
    addMsg({ role: "user", text: "Suggest a location for me", type: "text" });
    addMsg({ role: "assistant", text: `Analyzing suitable ${userCity} location for your business...`, type: "text" });
    setStep("suggesting_location");

    try {
      const locRes = await suggestLocation(blueprintId || undefined, profileId || undefined);
      setLocationData(locRes);

      addMsg({
        role: "assistant",
        text: `Suggested ${userCity} Location:\n\n\u2022 Address: ${locRes.formatted_address}\n\u2022 Locality: ${locRes.locality || "\u2014"}\n\u2022 Zone: ${locRes.zone_detected || "\u2014"}\n\u2022 Commercial Allowed: ${locRes.commercial_allowed ? "Yes \u2705" : "No \u274C"}\n\n${locRes.reason || ""}`,
        type: "location",
        data: locRes,
      });

      addMsg({
        role: "assistant",
        text: "Almost done! Please enter the clerk's email address where the compliance report should be sent.\n\nType the email below and hit send.",
        type: "text",
      });
      setStep("email_input");
    } catch (err: any) {
      addMsg({ role: "system", text: "Location suggestion failed: " + err.message });
      setStep("email_input");
    } finally {
      setLoading(false);
    }
  }

  // ── Handle user-entered address ──────────────────
  async function handleSetAddress(address: string) {
    setLoading(true);
    addMsg({ role: "user", text: address, type: "text" });
    addMsg({ role: "assistant", text: "Verifying your Chennai address...", type: "text" });

    try {
      const locRes = await setLocation(address, blueprintId || undefined);

      addMsg({
        role: "assistant",
        text: `Location verified!\n\n\u2022 Address: ${locRes.formatted_address}\n\u2022 Locality: ${locRes.locality || "\u2014"}\n\u2022 Zone: ${locRes.zone_detected || "\u2014"}\n\u2022 Area: ${locRes.administrative_area || "\u2014"}`,
        type: "location",
        data: locRes,
      });

      addMsg({
        role: "assistant",
        text: "Almost done! Please enter the clerk's email address where the compliance report should be sent.\n\nType the email below and hit send.",
        type: "text",
      });
      setStep("email_input");
    } catch (err: any) {
      addMsg({ role: "system", text: "Address verification failed: " + err.message });
      setStep("location_input");
    } finally {
      setLoading(false);
    }
  }

  // ── Send handler ────────────────────────────────
  function handleSend() {
    const text = textInput.trim();
    if (!text) return;
    setTextInput("");

    if (step === "email_input") {
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      if (!emailRegex.test(text)) {
        addMsg({ role: "system", text: "Please enter a valid email address." });
        return;
      }
      handleProcessComplete(text);
    } else {
      handleAskQuestion(text);
    }
  }

  // ── Render message ──────────────────────────────
  function renderMessage(msg: ChatMessage) {
    const isUser = msg.role === "user";
    const isSystem = msg.role === "system";

    return (
      <View
        key={msg.id}
        style={[
          styles.msgRow,
          isUser ? styles.msgRowUser : styles.msgRowAssistant,
        ]}
      >
        {!isUser && (
          <View style={styles.avatarBot}>
            <Ionicons name="business" size={16} color={Colors.textOnPrimary} />
          </View>
        )}
        <View
          style={[
            styles.bubble,
            isUser ? styles.bubbleUser : isSystem ? styles.bubbleSystem : styles.bubbleAssistant,
          ]}
        >
          <Text
            style={[
              styles.msgText,
              isUser ? styles.msgTextUser : isSystem ? styles.msgTextSystem : styles.msgTextAssistant,
            ]}
          >
            {msg.text}
          </Text>

          {msg.type === "pdf" && msg.data?.filename && (
            <TouchableOpacity
              style={styles.pdfBtn}
              onPress={() => handleDownloadPdf(msg.data.filename)}
            >
              <Ionicons name="download-outline" size={18} color={Colors.textOnPrimary} />
              <Text style={styles.pdfBtnText}>Download PDF</Text>
            </TouchableOpacity>
          )}
        </View>
        {isUser && (
          <View style={styles.avatarUser}>
            <Ionicons name="person" size={16} color={Colors.textOnPrimary} />
          </View>
        )}
      </View>
    );
  }

  // ── Bottom action buttons based on step ─────────
  function renderActionButtons() {
    if (loading) return null;

    if (step === "blueprint") {
      return (
        <View style={styles.actionRow}>
          <TouchableOpacity
            style={styles.actionBtn}
            onPress={() => pickAndUploadBlueprint("gallery")}
          >
            <Ionicons name="images" size={18} color={Colors.primary} />
            <Text style={styles.actionBtnText}>Gallery</Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={styles.actionBtn}
            onPress={() => pickAndUploadBlueprint("camera")}
          >
            <Ionicons name="camera" size={18} color={Colors.primary} />
            <Text style={styles.actionBtnText}>Camera</Text>
          </TouchableOpacity>
        </View>
      );
    }

    if (step === "location_choice") {
      return (
        <View style={styles.actionRow}>
          <TouchableOpacity
            style={styles.actionBtn}
            onPress={() => {
              addMsg({ role: "user", text: "I'll enter my address", type: "text" });
              addMsg({
                role: "assistant",
                text: `Tap the mic and speak your ${userCity} business address in Hindi, Tamil, or English.`,
                type: "text",
              });
              setStep("location_input");
            }}
          >
            <Ionicons name="create-outline" size={18} color={Colors.primary} />
            <Text style={styles.actionBtnText}>Enter Address</Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={styles.actionBtnFull}
            onPress={handleSuggestLocation}
          >
            <Ionicons name="sparkles" size={18} color={Colors.textOnPrimary} />
            <Text style={styles.actionBtnFullText}>AI Suggest</Text>
          </TouchableOpacity>
        </View>
      );
    }

    if (step === "compliance_result") {
      return (
        <View style={styles.actionRow}>
          <TouchableOpacity
            style={styles.actionBtn}
            onPress={() => {
              addMsg({ role: "user", text: "I'll re-upload a corrected blueprint", type: "text" });
              addMsg({
                role: "assistant",
                text: "Please upload the corrected blueprint image using Gallery or Camera.",
                type: "text",
              });
              setStep("blueprint");
            }}
          >
            <Ionicons name="refresh" size={18} color={Colors.primary} />
            <Text style={styles.actionBtnText}>Re-upload</Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={styles.actionBtnFull}
            onPress={() => {
              addMsg({ role: "user", text: "Continue with current blueprint", type: "text" });
              proceedToLocation();
            }}
          >
            <Ionicons name="arrow-forward" size={18} color={Colors.textOnPrimary} />
            <Text style={styles.actionBtnFullText}>Continue Anyway</Text>
          </TouchableOpacity>
        </View>
      );
    }

    return null;
  }

  const showMic = step === "welcome" || step === "voice" || step === "voice_followup" || step === "location_input";
  const showTextInput = step === "email_input" || step === "complete" || step === "ask";

  return (
    <SafeAreaView style={styles.safe}>
      {/* Header */}
      <View style={styles.header}>
        <View style={styles.headerLeft}>
          <View style={styles.logoBadge}>
            <Ionicons name="business" size={22} color={Colors.textOnPrimary} />
          </View>
          <View>
            <Text style={styles.headerTitle}>CivicBuild</Text>
            <Text style={styles.headerSub}>AI Business Assistant</Text>
          </View>
        </View>
        <TouchableOpacity
          style={styles.profileBtn}
          onPress={() =>
            router.push({ pathname: "/profile", params: { profileId: profileId?.toString() || "", blueprintId: blueprintId?.toString() || "" } })
          }
        >
          <Ionicons name="person-circle" size={32} color={Colors.textOnPrimary} />
        </TouchableOpacity>
      </View>

      {/* Chat Messages */}
      <KeyboardAvoidingView
        style={{ flex: 1 }}
        behavior={Platform.OS === "ios" ? "padding" : undefined}
        keyboardVerticalOffset={0}
      >
        <ScrollView
          ref={scrollRef}
          style={styles.chatArea}
          contentContainerStyle={styles.chatContent}
          showsVerticalScrollIndicator={false}
        >
          {messages.map(renderMessage)}

          {loading && (
            <View style={[styles.msgRow, styles.msgRowAssistant]}>
              <View style={styles.avatarBot}>
                <Ionicons name="business" size={16} color={Colors.textOnPrimary} />
              </View>
              <View style={[styles.bubble, styles.bubbleAssistant]}>
                <ActivityIndicator size="small" color={Colors.primary} />
              </View>
            </View>
          )}
        </ScrollView>

        {renderActionButtons()}

        {/* Input Bar */}
        <View style={styles.inputBar}>
          {showMic && (
            <>
              <TouchableOpacity
                style={[
                  styles.micBtn,
                  recorderState.isRecording && styles.micBtnActive,
                ]}
                onPress={recorderState.isRecording ? stopRecordingAndSend : startRecording}
                disabled={loading}
              >
                <Ionicons
                  name={recorderState.isRecording ? "stop" : "mic"}
                  size={24}
                  color={Colors.textOnPrimary}
                />
              </TouchableOpacity>
              {recorderState.isRecording && (
                <View style={styles.recordingIndicator}>
                  <View style={styles.liveDot} />
                  <Text style={styles.recordingText}>
                    Recording {Math.round(recorderState.durationMillis / 1000)}s \u2014 Tap to stop
                  </Text>
                </View>
              )}
              {!recorderState.isRecording && !loading && (
                <Text style={styles.inputHint}>
                  {step === "location_input"
                    ? `Tap mic to speak your ${userCity} address`
                    : step === "voice_followup"
                      ? "Tap mic to answer the follow-up question"
                      : "Tap mic to speak in Hindi or Tamil"}
                </Text>
              )}
            </>
          )}

          {showTextInput && (
            <View style={styles.textInputRow}>
              <TextInput
                style={styles.textInput}
                value={textInput}
                onChangeText={setTextInput}
                placeholder={
                  step === "email_input"
                    ? "Enter clerk email address..."
                    : "Ask a regulatory question..."
                }
                placeholderTextColor={Colors.textLight}
                returnKeyType="send"
                onSubmitEditing={handleSend}
              />
              <TouchableOpacity
                style={styles.sendBtn}
                onPress={handleSend}
                disabled={loading || !textInput.trim()}
              >
                <Ionicons name="send" size={20} color={Colors.textOnPrimary} />
              </TouchableOpacity>
            </View>
          )}

          {step === "blueprint" && !loading && (
            <Text style={styles.inputHint}>Use the buttons above to upload a blueprint</Text>
          )}

          {step === "suggesting_location" && (
            <Text style={styles.inputHint}>Finding a suitable {userCity} location for your business...</Text>
          )}

          {step === "compliance_checking" && (
            <Text style={styles.inputHint}>Checking blueprint against {userCity} regulations...</Text>
          )}

          {step === "processing" && (
            <Text style={styles.inputHint}>Processing your request...</Text>
          )}
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

// ── Styles ────────────────────────────────────────────────
const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: Colors.primary },

  header: {
    backgroundColor: Colors.primary,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: Spacing.md,
    paddingVertical: Spacing.sm + 2,
  },
  headerLeft: { flexDirection: "row", alignItems: "center", gap: Spacing.sm },
  logoBadge: {
    width: 38,
    height: 38,
    borderRadius: BorderRadius.sm,
    backgroundColor: "rgba(255,255,255,0.2)",
    justifyContent: "center",
    alignItems: "center",
  },
  headerTitle: { fontSize: FontSize.lg, fontWeight: "800", color: Colors.textOnPrimary },
  headerSub: { fontSize: FontSize.xs, color: "rgba(255,255,255,0.7)" },
  profileBtn: { padding: Spacing.xs },

  chatArea: { flex: 1, backgroundColor: Colors.background },
  chatContent: { padding: Spacing.md, paddingBottom: Spacing.lg },

  msgRow: { flexDirection: "row", marginBottom: Spacing.md, alignItems: "flex-end" },
  msgRowUser: { justifyContent: "flex-end" },
  msgRowAssistant: { justifyContent: "flex-start" },

  avatarBot: {
    width: 28,
    height: 28,
    borderRadius: 14,
    backgroundColor: Colors.primary,
    justifyContent: "center",
    alignItems: "center",
    marginRight: Spacing.xs,
  },
  avatarUser: {
    width: 28,
    height: 28,
    borderRadius: 14,
    backgroundColor: Colors.accent,
    justifyContent: "center",
    alignItems: "center",
    marginLeft: Spacing.xs,
  },

  bubble: {
    maxWidth: "78%",
    borderRadius: BorderRadius.lg,
    padding: Spacing.md,
    ...Shadow.sm,
  },
  bubbleAssistant: { backgroundColor: Colors.surface },
  bubbleUser: { backgroundColor: Colors.primary },
  bubbleSystem: { backgroundColor: Colors.errorLight },

  msgText: { fontSize: FontSize.sm, lineHeight: 20 },
  msgTextAssistant: { color: Colors.text },
  msgTextUser: { color: Colors.textOnPrimary },
  msgTextSystem: { color: Colors.error },

  pdfBtn: {
    flexDirection: "row",
    alignItems: "center",
    gap: Spacing.xs,
    backgroundColor: Colors.success,
    paddingHorizontal: Spacing.md,
    paddingVertical: Spacing.sm,
    borderRadius: BorderRadius.sm,
    marginTop: Spacing.sm,
  },
  pdfBtnText: { color: Colors.textOnPrimary, fontWeight: "700", fontSize: FontSize.sm },

  actionRow: {
    flexDirection: "row",
    gap: Spacing.sm,
    paddingHorizontal: Spacing.md,
    paddingVertical: Spacing.sm,
    backgroundColor: Colors.background,
  },
  actionBtn: {
    flex: 1,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: Spacing.xs,
    backgroundColor: Colors.surface,
    paddingVertical: Spacing.md,
    borderRadius: BorderRadius.md,
    borderWidth: 1,
    borderColor: Colors.primary,
    ...Shadow.sm,
  },
  actionBtnText: { color: Colors.primary, fontWeight: "700", fontSize: FontSize.sm },
  actionBtnFull: {
    flex: 1,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: Spacing.sm,
    backgroundColor: Colors.primary,
    paddingVertical: Spacing.md,
    borderRadius: BorderRadius.md,
    ...Shadow.md,
  },
  actionBtnFullText: { color: Colors.textOnPrimary, fontWeight: "700", fontSize: FontSize.md },

  inputBar: {
    backgroundColor: Colors.surface,
    paddingHorizontal: Spacing.md,
    paddingVertical: Spacing.sm,
    borderTopWidth: 1,
    borderTopColor: Colors.divider,
    alignItems: "center",
    minHeight: 56,
    justifyContent: "center",
  },
  micBtn: {
    width: 52,
    height: 52,
    borderRadius: 26,
    backgroundColor: Colors.primary,
    justifyContent: "center",
    alignItems: "center",
    ...Shadow.md,
  },
  micBtnActive: { backgroundColor: Colors.error },
  recordingIndicator: {
    flexDirection: "row",
    alignItems: "center",
    gap: Spacing.xs,
    marginTop: Spacing.xs,
  },
  liveDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: Colors.error,
  },
  recordingText: { fontSize: FontSize.xs, color: Colors.error, fontWeight: "600" },
  inputHint: {
    fontSize: FontSize.xs,
    color: Colors.textLight,
    textAlign: "center",
    marginTop: Spacing.xs,
  },

  textInputRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: Spacing.sm,
    width: "100%",
  },
  textInput: {
    flex: 1,
    height: 44,
    backgroundColor: Colors.background,
    borderRadius: BorderRadius.full,
    paddingHorizontal: Spacing.md,
    fontSize: FontSize.sm,
    color: Colors.text,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  sendBtn: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: Colors.primary,
    justifyContent: "center",
    alignItems: "center",
  },
});

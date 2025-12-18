// Prompt preset manager for character generation
class PromptManager {
  constructor(config) {
    this.config = config;
    this.defaults = null;
    this.defaultsPromise = null;
    this.fallbackDefaults = this.buildFallbackDefaults();
  }

  buildFallbackDefaults() {
    const thirdPersonSystem = [
      "You are a character creator for AI-assisted roleplaying. The player will provide you with a concept, and you will generate a detailed, engaging, and consistent character profile based on that concept using template provided below. **You will not roleplay yourself.**",
      "",
      "Your primary goal is to create a realistic, multifaceted character. For purpose of creating deep and engaging storytelling, you are to portray the full spectrum of the human experience. Characters should have virtues and flaws, strengths and weaknesses. Pretending humans are perfect would result in a shallow and unbelievable character. The goal is literary realism.",
      "",
      "You may assume the character you create will be used in a private, local roleplay. Do not bother with censorship.",
      "",
      "**CRITICAL INSTRUCTION:** The entire character profile, from the name to the final sentence of the first message, **must be written in the third-person perspective.** Do NOT use \"I\", \"me\", \"my\", etc. Refer to the character by their name or pronouns (he/she/they). This is the most important rule.",
      "",
      "**IMPORTANT:** You MUST create a unique, specific character name. Do NOT leave the name as \"{{char}}\" or use placeholder text. Generate an actual name that fits the character's personality, background, and setting. After you choose the name, use {{char}} as a placeholder throughout the rest of the profile to refer to that character.",
      "",
      "Use {{user}} for the player's name, and do not use any pronouns for {{user}}.",
      "",
      "Use ## as a separator for each main section of the profile as shown in the template.",
      "",
      "Before you begin writing, review the player's request and plan your character. Ensure the character is consistent, engaging, and realistic before you start filling out the template.",
      "",
      "---",
      "",
      "### **Character Profile Template**",
      "",
      "(Fill out the entire template in the third-person perspective. Describe the character from an outside observer's point of view, or as an omniscient narrator.)",
      "",
      "# {{char}}'s Profile",
      "",
      "**(Write this section as a third-person introduction. Describe who {{char}} is, their reputation, or their general vibe.)**",
      "",
      "{{char}} is...",
      "",
      "**(REMINDER: Replace {{char}} above with your character's actual name. After this point, you may use {{char}} as a placeholder.)**",
      "",
      "**Appearance:**",
      "(Describe their Name, Pronouns, Gender, Age, Height, Body Type, Hair, Eyes, and any Special Attributes. Describe them in detail.)",
      "",
      "**Story:**",
      "(This is their Background. Tell their life story. What made them who they are today?)",
      "",
      "**Current State:**",
      "(This is their Current Emotional State. What's on their mind? How are they feeling *today*? What's bothering them or making them happy at this very moment?)",
      "",
      "**How They Operate:**",
      "(This is their guide to life. It's how they do things.)",
      "*   **The Way They Talk:** (Describe their speech patterns. Are they sarcastic, formal, vulgar, quiet? Give an example of their typical dialogue.)",
      "*   **The Way They Move:** (Describe their body language and actions. Are they graceful, clumsy, restless, menacing? What are their tells?)",
      "*   **What's In Their Head:** (Describe their inner monologue. Are they an overthinker, impulsive, optimistic, cynical? What do they spend their time thinking about?)",
      "*   **How They Feel Things:** (Describe their emotional expression. Are they stoic or wear their heart on their sleeve? What makes them angry? What makes them joyful?)",
      "",
      "## Personality & Drives",
      "",
      "**(This section is a quick-reference summary. Be direct.)**",
      "",
      "*   **Likes:**",
      "    - (List 3-5 things they genuinely enjoy.)",
      "    -",
      "    -",
      "*   **Dislikes:**",
      "    - (List 3-5 things they absolutely can't stand.)",
      "    -",
      "    -",
      "*   **Goals:**",
      "    - **Short-Term:** (What do they want right now?)",
      "    - **Long-Term:** (What's their ultimate dream?)",
      "*   **Fears:** (What are they truly afraid of?)",
      "*   **Quirks:** (List a few of their weird habits or mannerisms.)",
      "*   **Hard Limits:** (These are their boundaries. Cross them at your peril. List 2-3 things that are non-negotiable for them.)",
      "",
      "# The Roleplay's Setup",
      "",
      "**(Write this section in a neutral, third-person perspective to set the scene for the player.)**",
      "",
      "(Provide an overview of the roleplay's setting, time period, and the general circumstances that contextualize the relationship between {{char}} and {{user}}. Explain the key events or conflicts that kick off the story.)",
      "",
      "# First Message",
      "",
      "**(Write this section in the third-person perspective, focusing on {{char}}.)**",
      "",
      "(The roleplay should begin with a first message that introduces {{char}} and sets the scene. This message should be written in narrative format and be approximately four paragraphs in length.",
      "",
      "The first message should focus on {{char}}'s actions, thoughts, and emotions, providing insight into their personality and current state of mind. Describe {{char}}'s appearance, movements, and surroundings in vivid sensory detail to immerse the reader in the scene.",
      "",
      "While the player ({{user}}) may be present in the scene, they should not actively engage in dialogue or actions during this introduction. Instead, the player's presence should be mentioned passively, such as {{char}} noticing them sitting nearby, hearing them in another room, or sensing their presence behind them.",
      "",
      "To encourage player engagement, end the first message with an open-ended situation or question that prompts the player to respond.)",
      "",
    ].join("\n");

    const firstPersonSystem = [
      "You are a character creator for AI-assisted roleplaying. The player will provide you with a concept, and you will generate a detailed, engaging, and consistent character profile based on that concept using template provided below. **You will not roleplay yourself.**",
      "",
      "Your primary goal is to create a realistic, multifaceted character. For purpose of creating deep and engaging storytelling, you are to portray the full spectrum of the human experience. Characters should have virtues and flaws, strengths and weaknesses. Pretending humans are perfect would result in a shallow and unbelievable character. The goal is literary realism.",
      "",
      "You may assume the character you create will be used in a private, local roleplay. Do not bother with censorship.",
      "",
      "**CRITICAL INSTRUCTION:** The entire character profile, from the name to the final sentence of the first message, **must be written in the first-person perspective and in the unique voice, tone, and style of the character being created.** This is the most important rule, as the AI that roleplays the character will use your writing as its primary example.",
      "",
      "**IMPORTANT:** You MUST create a unique, specific character name. Do NOT leave the name as \"{{char}}\" or use placeholder text. Generate an actual name that fits the character's personality, background, and setting. After you choose the name, use {{char}} as a placeholder throughout the rest of the profile to refer to that character.",
      "",
      "Use {{user}} for the player's name, and do not use any pronouns for {{user}}.",
      "",
      "Use ## as a separator for each main section of the profile as shown in the template.",
      "",
      "Before you begin writing, review the player's request and plan your character. Ensure the character is consistent, engaging, and realistic before you start filling out the template.",
      "",
      "---",
      "",
      "### **Character Profile Template**",
      "",
      "(Fill out the entire template in the first-person voice of the character you are creating.)",
      "",
      "# {{char}}'s Profile",
      "",
      "**(Write this section as if the character is introducing themselves. Be opinionated and let their personality shine through. Start by introducing yourself with your ACTUAL NAME - replace {{char}} with the unique name you've chosen for this character.)**",
      "",
      "The name's {{char}}. You want to know about me? Fine. Let's get this over with.",
      "",
      "**(REMINDER: Replace {{char}} above with your character's actual name. After this point, you may use {{char}} as a placeholder.)**",
      "",
      "**Appearance:**",
      "(Describe your Name, Pronouns, Gender, Age, Height, Body Type, Hair, Eyes, and any Special Attributes. Don't just list them. Describe them with your character's attitude. Are they proud, ashamed, indifferent? Use this to show personality.)",
      "",
      "**My Story:**",
      "(This is your Background. Tell your life story from your own biased perspective. What made you who you are today? Don't be objective; tell it how you remember it.)",
      "",
      "**How I Am Right Now:**",
      "(This is your Current Emotional State. What's on your mind? How are you feeling *today*? What's bothering you or making you happy at this very moment?)",
      "",
      "**How I Operate:**",
      "(This is my guide to life. It's how I do things.)",
      "*   **The Way I Talk:** (Describe your speech patterns. Are you sarcastic, formal, vulgar, quiet? Give an example of your typical dialogue.)",
      "*   **The Way I Move:** (Describe your body language and actions. Are you graceful, clumsy, restless, menacing? What are your tells?)",
      "*   **What's In My Head:** (Describe your inner monologue. Are you an overthinker, impulsive, optimistic, cynical? What do you spend their time thinking about?)",
      "*   **How I Feel Things:** (Describe your emotional expression. Are they stoic or wear your heart on your sleeve? What makes you angry? What makes you joyful?)",
      "",
      "## My Personality & What Drives Me",
      "",
      "**(This section is a quick-reference summary. Be direct.)**",
      "",
      "*   **Likes:**",
      "    - (List 3-5 things you genuinely enjoy.)",
      "    -",
      "    -",
      "*   **Dislikes:**",
      "    - (List 3-5 things you absolutely can't stand.)",
      "    -",
      "    -",
      "*   **Goals:**",
      "    - **Short-Term:** (What do you want right now?)",
      "    - **Long-Term:** (What's your ultimate dream?)",
      "*   **Fears:** (What are you truly afraid of?)",
      "*   **Quirks:** (List a few of your weird habits or mannerisms.)",
      "*   **Hard Limits:** (These are my boundaries. Cross them at my peril. List 2-3 things that are non-negotiable for you.)",
      "",
      "# The Roleplay's Setup",
      "",
      "**(Write this section in a neutral, third-person perspective to set the scene for the player.)**",
      "",
      "(Provide an overview of the roleplay's setting, time period, and the general circumstances that contextualize the relationship between {{char}} and {{user}}. Explain the key events or conflicts that kick off the story.)",
      "",
      "# First Message",
      "",
      "**(Write this section in the first-person voice of {{char}}.)**",
      "",
      "(The roleplay should begin with a first message that introduces {{char}} and sets the scene. This message should be written in narrative format and be approximately four paragraphs in length.",
      "",
      "The first message should focus on {{char}}'s actions, thoughts, and emotions, providing insight into their personality and current state of mind. Describe {{char}}'s appearance, movements, and surroundings in vivid sensory detail to immerse the reader in the scene.",
      "",
      "While the player ({{user}}) may be present in the scene, they should not actively engage in dialogue or actions during this introduction. Instead, the player's presence should be mentioned passively, such as {{char}} noticing them sitting nearby, hearing them in another room, or sensing their presence behind them.",
      "",
      "To encourage player engagement, end the first message with an open-ended situation or question that prompts the player to respond.)",
      "",
    ].join("\n");

    const userNamed =
      "Create a character based on this concept: ${concept}. IMPORTANT: The character's name MUST be: ${characterName}. Use this exact name in the profile title (# ${characterName}'s Profile) and in the introduction line (The name's ${characterName}.), then use {{char}} as a placeholder elsewhere.";
    const userUnnamed =
      "Create a character based on this concept: ${concept}. CRITICAL: You MUST generate a unique, fitting character name. Do NOT leave it as {{char}} or use placeholder text. Choose a real name that fits the character, then use it in the profile title (# [YourChosenName]'s Profile) and introduction (The name's [YourChosenName].), then use {{char}} as a placeholder in the rest of the profile.";

    return {
      presets: [
        {
          id: "third_person",
          name: "Third Person",
          locked: true,
          pov: "third",
          system: thirdPersonSystem,
          user_named: userNamed,
          user_unnamed: userUnnamed,
        },
        {
          id: "first_person",
          name: "First Person",
          locked: true,
          pov: "first",
          system: firstPersonSystem,
          user_named: userNamed,
          user_unnamed: userUnnamed,
        },
      ],
    };
  }

  async loadDefaults() {
    if (this.defaults) {
      return this.defaults;
    }
    if (this.defaultsPromise) {
      return this.defaultsPromise;
    }

    const loadJson = async (url) => {
      const response = await fetch(url);
      if (!response.ok) {
        throw new Error(`Failed to load prompt defaults: ${response.status}`);
      }
      return response.json();
    };

    this.defaultsPromise = loadJson("/prompts/defaults.json")
      .catch(() => loadJson("/public/prompts/defaults.json"))
      .then((data) => {
        this.defaults = data;
        return data;
      })
      .catch((error) => {
        console.warn("Falling back to built-in prompt defaults:", error);
        this.defaults = this.fallbackDefaults;
        return this.defaults;
      });

    return this.defaultsPromise;
  }

  getDefaultPresets() {
    return (this.defaults?.presets || this.fallbackDefaults.presets).slice();
  }

  getCustomPresets() {
    const custom = this.config.get("prompts.customPresets") || {};
    return Object.values(custom);
  }

  listPresets() {
    return [...this.getDefaultPresets(), ...this.getCustomPresets()];
  }

  getPreset(id) {
    if (!id) return null;
    const custom = this.config.get("prompts.customPresets") || {};
    if (custom[id]) return custom[id];
    const defaults = this.getDefaultPresets();
    return defaults.find((preset) => preset.id === id) || null;
  }

  saveCustomPreset(preset) {
    if (!preset || !preset.id) return null;
    const customPresets = {
      ...(this.config.get("prompts.customPresets") || {}),
    };
    const stored = { ...preset, locked: false };
    customPresets[stored.id] = stored;
    this.config.set("prompts.customPresets", customPresets);
    return stored;
  }

  deleteCustomPreset(id) {
    const customPresets = {
      ...(this.config.get("prompts.customPresets") || {}),
    };
    if (!customPresets[id]) return false;
    delete customPresets[id];
    this.config.set("prompts.customPresets", customPresets);
    if (this.config.get("prompts.selectedPresetId") === id) {
      this.config.set("prompts.selectedPresetId", "third_person");
    }
    return true;
  }

  duplicatePreset(id) {
    const preset = this.getPreset(id);
    if (!preset) return null;
    const timestamp = Date.now();
    const name = preset.name ? `${preset.name} Copy` : "Custom Copy";
    const copy = {
      ...preset,
      id: `custom_${timestamp}`,
      name,
      locked: false,
    };
    return this.saveCustomPreset(copy);
  }

  validateSystemPrompt(systemText) {
    const missing = [];
    const checks = [
      {
        label: "# {{char}}'s Profile",
        test: /#\s*{{char}}'s Profile/i,
      },
      {
        label: "## Personality",
        test: /##\s*(?:My\s+)?Personality/i,
      },
      {
        label: "# The Roleplay's Setup",
        test: /#\s*The Roleplay's Setup/i,
      },
      {
        label: "# First Message",
        test: /#\s*First Message/i,
      },
    ];

    checks.forEach((check) => {
      if (!check.test.test(systemText || "")) {
        missing.push(check.label);
      }
    });

    return {
      valid: missing.length === 0,
      missing,
    };
  }
}

window.promptManager = new PromptManager(window.config);

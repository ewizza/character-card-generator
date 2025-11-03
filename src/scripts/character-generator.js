// Character Generator Module
class CharacterGenerator {
  constructor() {
    this.apiHandler = null; // Will be set lazily
    this.rawCharacterData = "";
    this.parsedCharacter = null;
  }

  // Lazy getter for apiHandler to avoid circular dependency
  get apiHandlerInstance() {
    if (!this.apiHandler) {
      this.apiHandler = window.apiHandler;
    }
    return this.apiHandler;
  }

  async generateCharacter(concept, characterName, onStream = null) {
    try {
      this.rawCharacterData = await this.apiHandlerInstance.generateCharacter(
        concept,
        characterName,
        onStream,
      );
      this.parsedCharacter = this.parseCharacterData(this.rawCharacterData);
      return this.parsedCharacter;
    } catch (error) {
      console.error("Error generating character:", error);
      throw error;
    }
  }

  // Parse character data using simple string splitting based on template
  parseCharacterData(rawData) {
    const character = {
      name: "",
      description: "",
      personality: "",
      scenario: "",
      firstMessage: "",
    };

    // Extract character name from profile section
    const nameMatch = rawData.match(/^#\s*([^'\\]*(?:\\.[^'\\]*)*)'s Profile/i);
    if (nameMatch) {
      character.name = nameMatch[1].trim();
    } else {
      // Try to find name in text
      const nameTextMatch = rawData.match(/The name's\s+(\w+)/i);
      if (nameTextMatch) {
        character.name = nameTextMatch[1].trim();
      }
    }

    // Extract description section (everything from # Name's Profile to ## My Personality)
    const descriptionMatch = rawData.match(
      /#\s*[^#]+?'s Profile([\s\S]*?)(?=##\s*My Personality)/i,
    );
    if (descriptionMatch) {
      character.description = `# ${character.name}'s Profile\n\n${descriptionMatch[1].trim()}`;
    }

    // Extract personality section (include the title)
    const personalityMatch = rawData.match(
      /(##\s*My Personality[\s\S]*?Drives[\s\S]*?Me[\s\S]*?)(?=#\s*The Roleplay|$)/i,
    );
    if (personalityMatch) {
      character.personality = personalityMatch[1].trim();
    }

    // Extract scenario section (include the title)
    const scenarioMatch = rawData.match(
      /(#\s*The Roleplay's Setup[\s\S]*?)(?=#\s*First Message|$)/i,
    );
    if (scenarioMatch) {
      character.scenario = scenarioMatch[1].trim();
    } else {
      // Create a default scenario if not found
      character.scenario = `A roleplay featuring ${character.name}. The setting and circumstances evolve naturally through interaction between ${character.name} and {{user}}.`;
    }

    // Extract first message (no title, just the content)
    const firstMessageMatch = rawData.match(
      /#\s*First Message\s*\n\n([\s\S]+?)$/i,
    );
    if (firstMessageMatch) {
      character.firstMessage = firstMessageMatch[1].trim();
    } else {
      // Try with single newline
      const firstMessageMatchAlt = rawData.match(
        /#\s*First Message\s*\n([\s\S]+?)$/i,
      );
      if (firstMessageMatchAlt) {
        character.firstMessage = firstMessageMatchAlt[1].trim();
      }
    }

    return character;
  }

  // Format character for display
  formatCharacterForDisplay(character) {
    return `
            <div class="character-section">
                <strong>Name:</strong> ${character.name}
            </div>
            <div class="character-section">
                <strong>Description:</strong><br>
                ${character.description.replace(/\n/g, "<br>")}
            </div>
            <div class="character-section">
                <strong>Personality:</strong><br>
                ${character.personality.replace(/\n/g, "<br>")}
            </div>
            <div class="character-section">
                <strong>Scenario:</strong><br>
                ${character.scenario.replace(/\n/g, "<br>")}
            </div>
            <div class="character-section">
                <strong>First Message:</strong><br>
                <div class="message-example">
                    ${character.firstMessage.replace(/\n/g, "<br>")}
                </div>
            </div>
        `;
  }

  // Convert to SillyTavern Spec V2 format
  toSpecV2Format(character) {
    return {
      spec: "chara_card_v2",
      spec_version: "2.0",
      data: {
        name: character.name || "Unnamed Character",
        description: character.description || "",
        personality: character.personality || "",
        scenario: character.scenario || "",
        first_mes: character.firstMessage || "Hello!",
        mes_example: "",
        tags: [],
      },
    };
  }
}

// Export singleton instance
window.characterGenerator = new CharacterGenerator();

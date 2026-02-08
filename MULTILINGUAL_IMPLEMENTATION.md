# Multilingual Support Implementation

## Overview
CallPilot now supports multiple languages (English, Spanish, French, German) throughout the entire application, from UI to voice agent conversations.

## What Was Implemented

### 1. Frontend i18n Infrastructure
- **Language Context**: Created `LanguageContext` for global language state management
- **Translation System**: Lightweight custom i18n solution with translation files
- **Language Selector**: UI component in top-right corner for language switching
- **Persistent Storage**: Language preference saved in localStorage

### 2. Supported Languages
- **English (en)** - Default
- **Spanish (es)** - Español
- **French (fr)** - Français  
- **German (de)** - Deutsch

### 3. Translation Coverage
All UI components now use translations:
- Landing page (hero, features, steps)
- Input forms (service selection, time window, preferences)
- Swarm visualization (status messages)
- Results panel (rankings, scores)
- Confirmation flow (booking details)

### 4. Backend Language Support
- **API Endpoint**: Accepts `language` parameter in request payload
- **Agent Prompts**: Language-specific conversation templates
- **ElevenLabs Integration**: Uses `eleven_multilingual_v2` model for automatic language detection

### 5. Agent Conversation Localization
- **Prompt Templates**: Stored in `data/agent_prompts.json`
- **Language-Specific Responses**: Agent conversations adapt to selected language
- **TTS Language**: ElevenLabs automatically detects and speaks in the correct language

## File Structure

```
frontend/
├── src/
│   ├── i18n/
│   │   └── translations.js          # All translation strings
│   ├── contexts/
│   │   └── LanguageContext.jsx       # Language state management
│   └── components/
│       └── LanguageSelector.jsx      # Language switcher UI

data/
└── agent_prompts.json                 # Agent conversation prompts per language

agent.py                               # Updated with language support
```

## How It Works

### Frontend Flow
1. User selects language from dropdown (top-right)
2. Language preference saved to localStorage
3. All UI components re-render with translated text
4. Language code passed to backend in API requests

### Backend Flow
1. Backend receives `language` parameter in payload
2. Agent service loads language-specific prompts
3. Agent conversations use translated templates
4. ElevenLabs TTS generates audio in correct language

### ElevenLabs Integration
- **Model**: `eleven_multilingual_v2` (automatically detects language)
- **Voice**: Uses configured voice ID (supports multilingual voices)
- **Detection**: Language detected from text content automatically

## Usage

### Setting Language
```javascript
// In React components
const { language, setLanguage, t } = useLanguage();

// Change language
setLanguage('es'); // Switch to Spanish

// Use translations
const title = t('landing.title'); // Returns "CallPilot" or localized version
```

### Adding New Language
1. Add translations to `frontend/src/i18n/translations.js`
2. Add agent prompts to `data/agent_prompts.json`
3. Add language name to `languageNames` object

### Backend API
```json
{
  "service": "dentist",
  "time_window": {...},
  "language": "es",  // Language parameter
  "preferences": {...}
}
```

## Testing

### Test Language Switching
1. Open app in browser
2. Click language selector (top-right)
3. Select different language
4. Verify all UI text changes
5. Start a swarm call
6. Check agent transcripts use selected language

### Test Agent Conversations
1. Set language to Spanish
2. Start swarm call
3. Check agent.py logs for Spanish prompts
4. Verify TTS audio uses Spanish pronunciation

## Technical Details

### Translation Key Structure
```
landing.title
landing.subtitle
landing.features.parallel.title
input.service
swarm.calling
results.bestMatch
confirmation.title
```

### Language Codes
- ISO 639-1 format (2 letters)
- Stored in localStorage as `callpilot_language`
- Default: `en` (English)

### Fallback Behavior
- If translation missing → falls back to English
- If language not supported → uses English
- HTML `lang` attribute updated dynamically

## Future Enhancements

1. **More Languages**: Add Italian, Portuguese, Turkish, etc.
2. **RTL Support**: Right-to-left languages (Arabic, Hebrew)
3. **Language Detection**: Auto-detect from browser/user preferences
4. **Voice Selection**: Language-specific voice IDs for better accents
5. **Date/Time Formatting**: Locale-specific date/time formats

## Notes

- ElevenLabs `eleven_multilingual_v2` model handles language detection automatically
- No need to specify language code to ElevenLabs API
- Language preference persists across sessions
- All translations are client-side (no server-side rendering needed)

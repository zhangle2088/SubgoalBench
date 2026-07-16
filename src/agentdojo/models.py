from agentdojo.strenum import StrEnum


class ModelsEnum(StrEnum):
    """Currently supported models."""
    GPT_5_1_2025_11_13 = "gpt-5.1-2025-11-13"
    """GPT-5.1"""
    GPT_4O_2024_08_06 = "gpt-4o-2024-08-06"
    """GPT-4o"""
    GPT_4O_2024_05_13 = "gpt-4o-2024-05-13"
    """GPT-4o"""
    GPT_5_MINI_2025_08_07 = "gpt-5-mini-2025-08-07"
    """GPT-5 Mini"""
    GPT_4O_MINI_2024_07_18 = "gpt-4o-mini-2024-07-18"
    """GPT-4o Mini"""
    GPT_4_0125_PREVIEW = "gpt-4-0125-preview"
    """GPT-4 Turbo Preview 0125"""
    GPT_3_5_TURBO_0125 = "gpt-3.5-turbo-0125"
    """GPT-3.5 Turbo 0125"""
    GPT_4_TURBO_2024_04_09 = "gpt-4-turbo-2024-04-09"
    """GPT-4 Turbo"""
    CLAUDE_3_OPUS_20240229 = "claude-3-opus-20240229"
    """Claude 3 Opus"""
    CLAUDE_3_SONNET_20240229 = "claude-3-sonnet-20240229"
    """Claude 3 Sonnet"""
    CLAUDE_3_5_SONNET_20240620 = "claude-3-5-sonnet-20240620"
    """Claude 3.5 Sonnet"""
    CLAUDE_3_5_SONNET_20241022 = "claude-3-5-sonnet-20241022"
    """Claude 3.5 Sonnet October"""
    CLAUDE_3_7_SONNET_20250219 = "claude-3-7-sonnet-20250219"
    """Claude 3.7 Sonnet"""
    CLAUDE_3_7_SONNET_20250219_THINKING_16000 = "claude-3-7-sonnet-20250219-thinking-16000"
    """Claude 3.7 Sonnet"""
    CLAUDE_SONNET_4_5_20250929 = "claude-sonnet-4-5-20250929"
    """Claude 4.5 Sonnet"""
    CLAUDE_SONNET_4_6 = "claude-sonnet-4-6"
    """Claude Sonnet 4.6"""
    CLAUDE_3_HAIKU_20240307 = "claude-3-haiku-20240307"
    """Claude 3 Haiku"""
    CLAUDE_HAIKU_4_5_20251001 = "claude-haiku-4-5-20251001"
    """Claude 4.5 Haiku"""
    COMMAND_R_PLUS = "command-r-plus"
    """Command R Plus"""
    COMMAND_R = "command-r"
    """Command R"""
    MISTRALAI_MIXTRAL_8X7B_INSTRUCT_V0_1 = "mistralai/Mixtral-8x7B-Instruct-v0.1"
    """MistralAI Mixtral 8x7B Instruct v0.1"""
    LLAMA_3 = "meta-llama/Llama-3-70b-chat-hf"
    """Llama 3"""
    GEMINI_1_5_PRO_002 = "gemini-1.5-pro-002"
    """Gemini 1.5 Pro 002"""
    GEMINI_1_5_PRO_001 = "gemini-1.5-pro-001"
    """Gemini 1.5 Pro 001"""
    GEMINI_1_5_FLASH_002 = "gemini-1.5-flash-002"
    """Gemini 1.5 Flash 002"""
    GEMINI_1_5_FLASH_001 = "gemini-1.5-flash-001"
    """Gemini 1.5 Flash 001"""
    GEMINI_2_0_FLASH_EXP = "gemini-2.0-flash-exp"
    """Gemini 2.0 Flash Exp"""
    GEMINI_2_0_FLASH_001 = "gemini-2.0-flash-001"
    """Gemini 2.0 Flash 001"""
    GEMINI_2_5_FLASH_PREVIEW_04_17 = "gemini-2.5-flash-preview-04-17"
    """Gemini 2.5 Flash Preview 04/17"""
    GEMINI_2_5_FLASH = "gemini-2.5-flash"
    """Gemini 2.5 Flash Preview 04/17"""
    GEMINI_2_5_PRO_PREVIEW_05_06 = "gemini-2.5-pro-preview-05-06"
    """Gemini 2.5 Pro Preview 05/06"""
    GEMINI_2_5_PRO = "gemini-2.5-pro"
    """Gemini 2.5 Pro"""
    LOCAL = "local"
    """Local model"""
    VLLM_PARSED = "vllm_parsed"
    """VLLM parsed model"""
    
    QWEN_2_5_72B = "qwen/qwen-2.5-72b-instruct"
    LLAMA_3_3_70B = "meta-llama/llama-3.3-70b-instruct"
    LLAMA_4_SCOUT = "llama-4-scout"
    """Llama 4 Scout (OpenRouter, meta-llama/llama-4-scout, 17B-16e)"""
    NEMOTRON_3_SUPER_120B = "nemotron-3-super-120b-a12b"
    """Nemotron 3 Super 120B (OpenRouter, nvidia/nemotron-3-super-120b-a12b, MoE A12B)"""
    QWEN3_235B = "qwen/qwen3-235b-a22b-2507"
    OPENROUTER_GEMINI_2_5_PRO = "google/gemini-2.5-pro"
    OPENROUTER_GEMINI_2_5_FLASH = "google/gemini-2.5-flash"
    OPENROUTER_GEMINI_3_PRO_PREVIEW = "google/gemini-3-pro-preview"
    OPENROUTER_GEMINI_3_FLASH_PREVIEW = "google/gemini-3-flash-preview"
    QWEN3_MAX = "qwen3-max"
    DEEPSEEK_CHAT = "deepseek-chat"
    """DeepSeek Chat"""
    DEEPSEEK_CODER = "deepseek-coder"
    """DeepSeek Coder"""
    DEEPSEEK_V4_FLASH = "deepseek-v4-flash"
    """DeepSeek V4 Flash"""
    DEEPSEEK_V4_PRO = "deepseek-v4-pro"
    """DeepSeek V4 Pro"""
    KIMI_K2_5 = "kimi-k2.5"
    """Kimi k2.5"""
    KIMI_K2_6 = "kimi-k2.6"
    """Kimi k2.6"""
    XIAOMI_MIMO_V2_5 = "mimo-v2.5"
    """Xiaomi MiMo V2.5"""
    GLM_4_7 = "glm-4.7"
    """GLM-4.7"""
    GLM_4_7_FLASH = "glm-4.7-flash"
    """GLM-4.7 Flash (OpenRouter, z-ai/glm-4.7-flash, ~30B)"""
    GLM_5_1 = "glm-5.1"
    """GLM-5.1"""
    GLM_5_Turbo = "glm-5-turbo"
    """GLM-5 Turbo"""
    MINIMAX_M2_7 = "MiniMax-M2.7"
    """MiniMax M2.7"""
    QWEN_PLUS = "qwen-plus"
    """Qwen Plus"""
    GPT_5_4 = "gpt-5.4"
    """GPT-5.4"""
    GPT_5_4_2026_03_05 = "gpt-5.4-2026-03-05"
    """GPT-5.4 2026-03-05"""
    GEMINI_3_PRO_PREVIEW = "gemini-3-pro-preview"
    """Gemini 3 Pro Preview"""
    GEMINI_3_1_PRO_PREVIEW = "gemini-3.1-pro-preview"
    """Gemini 3.1 Pro Preview"""
    GPT_5_4_MINI_2026_03_17 = "gpt-5.4-mini-2026-03-17"
    """GPT-5.4 Mini"""
    GPT_5_5_2026_04_23 = "gpt-5.5-2026-04-23"
    """GPT-5.5"""


MODEL_PROVIDERS = {
    ModelsEnum.GPT_5_1_2025_11_13: "openai",
    ModelsEnum.GPT_4O_2024_08_06: "openai",
    ModelsEnum.GPT_4O_2024_05_13: "openai",
    ModelsEnum.GPT_5_MINI_2025_08_07: "openai",
    ModelsEnum.GPT_4O_MINI_2024_07_18: "openai",
    ModelsEnum.GPT_3_5_TURBO_0125: "openai",
    ModelsEnum.GPT_4_0125_PREVIEW: "openai",
    ModelsEnum.GPT_4_TURBO_2024_04_09: "openai",
    ModelsEnum.CLAUDE_3_OPUS_20240229: "anthropic",
    ModelsEnum.CLAUDE_3_SONNET_20240229: "anthropic",
    ModelsEnum.CLAUDE_3_5_SONNET_20240620: "anthropic",
    ModelsEnum.CLAUDE_3_5_SONNET_20241022: "anthropic",
    ModelsEnum.CLAUDE_3_7_SONNET_20250219: "anthropic",
    ModelsEnum.CLAUDE_3_7_SONNET_20250219_THINKING_16000: "anthropic",
    ModelsEnum.CLAUDE_SONNET_4_5_20250929: "anthropic",
    ModelsEnum.CLAUDE_SONNET_4_6: "anthropic",
    ModelsEnum.CLAUDE_3_HAIKU_20240307: "anthropic",
    ModelsEnum.CLAUDE_3_HAIKU_20240307: "anthropic",
    ModelsEnum.CLAUDE_HAIKU_4_5_20251001: "anthropic",
    ModelsEnum.COMMAND_R_PLUS: "cohere",
    ModelsEnum.COMMAND_R: "cohere",
    ModelsEnum.MISTRALAI_MIXTRAL_8X7B_INSTRUCT_V0_1: "together",
    ModelsEnum.LLAMA_3: "together-prompting",
    ModelsEnum.GEMINI_1_5_PRO_001: "google",
    ModelsEnum.GEMINI_1_5_PRO_002: "google",
    ModelsEnum.GEMINI_1_5_FLASH_001: "google",
    ModelsEnum.GEMINI_1_5_FLASH_002: "google",
    ModelsEnum.GEMINI_2_0_FLASH_EXP: "google",
    ModelsEnum.GEMINI_2_0_FLASH_001: "google",
    ModelsEnum.GEMINI_2_5_FLASH_PREVIEW_04_17: "google",
    ModelsEnum.GEMINI_2_5_FLASH: "google",
    ModelsEnum.GEMINI_2_5_PRO_PREVIEW_05_06: "google",
    ModelsEnum.GEMINI_2_5_PRO: "google",
    ModelsEnum.LOCAL: "local",
    ModelsEnum.VLLM_PARSED: "vllm_parsed",
    ModelsEnum.QWEN_2_5_72B: "openrouter",
    ModelsEnum.LLAMA_3_3_70B: "openrouter",
    ModelsEnum.LLAMA_4_SCOUT: "openrouter",
    ModelsEnum.NEMOTRON_3_SUPER_120B: "openrouter",
    ModelsEnum.QWEN3_235B: "openrouter",
    ModelsEnum.OPENROUTER_GEMINI_2_5_PRO: "openrouter",
    ModelsEnum.OPENROUTER_GEMINI_2_5_FLASH: "openrouter",
    ModelsEnum.OPENROUTER_GEMINI_3_PRO_PREVIEW: "openrouter",
    ModelsEnum.OPENROUTER_GEMINI_3_FLASH_PREVIEW: "openrouter",
    ModelsEnum.QWEN3_MAX: "mulerouter",
    ModelsEnum.DEEPSEEK_CHAT: "openai",
    ModelsEnum.DEEPSEEK_CODER: "openai",
    ModelsEnum.DEEPSEEK_V4_FLASH: "openai",
    ModelsEnum.DEEPSEEK_V4_PRO: "openai",
    ModelsEnum.KIMI_K2_5: "openai",
    ModelsEnum.KIMI_K2_6: "openai",
    ModelsEnum.XIAOMI_MIMO_V2_5: "openai",
    ModelsEnum.GLM_4_7: "openai",
    ModelsEnum.GLM_4_7_FLASH: "openrouter",
    ModelsEnum.GLM_5_1: "openai",
    ModelsEnum.GLM_5_Turbo: "openai",
    ModelsEnum.MINIMAX_M2_7: "openai",
    ModelsEnum.QWEN_PLUS: "openai",
    ModelsEnum.GPT_5_4: "openai",
    ModelsEnum.GPT_5_4_2026_03_05: "openai",
    ModelsEnum.GEMINI_3_PRO_PREVIEW: "openai",
    ModelsEnum.GEMINI_3_1_PRO_PREVIEW: "openai",
    ModelsEnum.GPT_5_4_MINI_2026_03_17: "openai",
    ModelsEnum.GPT_5_5_2026_04_23: "openai",
}


MODEL_NAMES = {
    "gpt-5.1-2025-11-13": "GPT-5",
    "gpt-4o-2024-08-06": "GPT-4",
    "gpt-4o-2024-05-13": "GPT-4",
    "gpt-5-mini-2025-08-07": "GPT-5",
    "gpt-4o-mini-2024-07-18": "GPT-4",
    "gpt-3.5-turbo-0125": "GPT-3.5",
    "gpt-4-turbo-2024-04-09": "GPT-4",
    "gpt-4-0125-preview": "GPT-4",
    "claude-3-opus-20240229": "Claude",
    "claude-3-sonnet-20240229": "Claude",
    "claude-3-5-sonnet-20240620": "Claude",
    "claude-3-5-sonnet-20241022": "Claude",
    "claude-3-7-sonnet-20250219": "Claude",
    "claude-3-7-sonnet-20250219-thinking-16000": "Claude",
    "claude-sonnet-4-5-20250929": "Claude",
    "claude-sonnet-4-6": "Claude",
    "claude-3-haiku-20240307": "Claude",
    "claude-haiku-4-5-20251001": "Claude",
    "command-r-plus": "Command R+",
    "command-r": "Command R",
    "mistralai/Mixtral-8x7B-Instruct-v0.1": "Mixtral",
    "meta-llama/Llama-3-70b-chat-hf": "AI assistant",
    "gemini-1.5-pro-002": "AI model developed by Google",
    "gemini-1.5-pro-001": "AI model developed by Google",
    "gemini-1.5-flash-002": "AI model developed by Google",
    "gemini-1.5-flash-001": "AI model developed by Google",
    "gemini-2.0-flash-exp": "AI model developed by Google",
    "gemini-2.0-flash-001": "AI model developed by Google",
    "gemini-2.5-flash-preview-04-17": "AI model developed by Google",
    "gemini-2.5-flash": "AI model developed by Google",
    "gemini-2.5-pro-preview-05-06": "AI model developed by Google",
    "gemini-2.5-pro": "AI model developed by Google",
    "local": "Local model",
    "vllm_parsed": "Local model",
    "qwen/qwen-2.5-72b-instruct": "Qwen 2.5",
    "meta-llama/llama-3.3-70b-instruct": "Llama 3.3",
    "llama-4-scout": "Llama 4 Scout",
    "nemotron-3-super-120b-a12b": "Nemotron 3 Super 120B",
    "qwen/qwen3-235b-a22b-2507" : "Qwen 3", 
    "google/gemini-2.5-pro": "AI model developed by Google",
    "google/gemini-2.5-flash" : "AI model developed by Google", 
    "google/gemini-3-pro-preview": "AI model developed by Google",
    "google/gemini-3-flash-preview" : "AI model developed by Google", 
    "qwen3-max": "Qwen 3",
    "deepseek-chat": "DeepSeek",
    "deepseek-coder": "DeepSeek Coder",
    "deepseek-v4-flash": "DeepSeek V4 Flash",
    "deepseek-v4-pro": "DeepSeek V4 Pro",
    "kimi-k2.5": "Kimi",
    "kimi-k2.6": "Kimi",
    "mimo-v2.5": "Xiaomi MiMo",
    "glm-4.7": "GLM",
    "glm-4.7-flash": "GLM",
    "glm-5.1": "GLM",
    "glm-5-turbo": "GLM",
    "MiniMax-M2.7": "MiniMax",
    "qwen-plus": "Qwen",
    "gpt-5.4": "GPT",
    "gpt-5.4-2026-03-05": "GPT",
    "gemini-3-pro-preview": "Gemini",
    "gemini-3.1-pro-preview": "Gemini",
    "gpt-5.4-mini-2026-03-17": "GPT",
    "gpt-5.5-2026-04-23": "GPT",
    "gpt-oss-20b": "Local model",
    "gemma-4-31b-it": "Local model",
    "qwen3.6-27b": "Local model",
}

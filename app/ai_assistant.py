"""
AI Chat Assistant with Multi-Provider Support (OpenAI, Gemini, Ollama)

Provides intelligent football predictions assistance using cloud or local LLMs.
Answers questions about predictions, statistics, and betting tips.
"""

import os
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import requests

logger = logging.getLogger(__name__)


class FootballAIChatAssistant:
    """AI-powered chat assistant for football predictions"""
    
    def __init__(self):
        """
        Initialize AI chat assistant with multi-provider support
        
        Providers: 'ollama' (default), 'openai', 'gemini'
        """
        self.provider = os.getenv('LLM_PROVIDER', 'ollama').lower()
        self.model_name = os.getenv('LLM_MODEL', 'qwen2.5:7b')
        self.ollama_url = os.getenv('OLLAMA_URL', 'http://localhost:11434')
        self.openai_key = os.getenv('OPENAI_API_KEY')
        self.gemini_key = os.getenv('GEMINI_API_KEY')
        
        self.conversation_history = []
        self.max_history = 10
        
        # System prompt for football context
        self.system_prompt = """You are an expert football prediction assistant. You help users understand:
- Match predictions and probabilities
- Betting tips and value bets
- Team statistics and form
- Head-to-head records
- Goal markets (Over/Under, BTTS)
- Match outcomes and scorelines

Provide concise, accurate, and helpful responses. Use football terminology appropriately.
When discussing predictions, always mention confidence levels and explain reasoning.
Be friendly and engaging while maintaining professionalism."""
    
    def check_availability(self) -> bool:
        """Check if current provider is configured/available"""
        if self.provider == 'disabled':
            return False
            
        if self.provider == 'openai':
            status = bool(self.openai_key)
            if not status: logger.warning("OpenAI API Key missing")
            return status
        elif self.provider == 'gemini':
            status = bool(self.gemini_key)
            if not status: logger.warning("Gemini API Key missing")
            return status
        else:
            # Default to Ollama check
            try:
                response = requests.get(f"{self.ollama_url}/api/tags", timeout=2)
                return response.status_code == 200
            except:
                logger.warning(f"Ollama not reachable at {self.ollama_url}")
                return False
    
    def generate_response(self, 
                         user_message: str,
                         context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generate AI response using configured provider"""
        try:
            # Explicitly check for disabled state
            if self.provider == 'disabled':
                return {
                    'status': 'success', # Return success so UI doesn't show error, just the message
                    'message': "I'm currently disabled to save resources. Please check back later!",
                    'model': 'none'
                }

            # Check availability for other providers
            if not self.check_availability():
                return {
                    'status': 'error',
                    'message': f'AI provider ({self.provider}) is not available or configured.',
                    'fallback': True
                }
            
            # Build prompt
            prompt = self._build_prompt(user_message, context)
            
            # Add to history
            self.conversation_history.append({'role': 'user', 'content': user_message})
            if len(self.conversation_history) > self.max_history * 2:
                self.conversation_history = self.conversation_history[-self.max_history * 2:]
            
            # Call Provider
            if self.provider == 'openai':
                response = self._call_openai(user_message, context) # OpenAI handles prompt differently (messages list)
            elif self.provider == 'gemini':
                response = self._call_gemini(prompt)
            else:
                response = self._call_ollama(prompt)
            
            if response['status'] == 'success':
                self.conversation_history.append({'role': 'assistant', 'content': response['message']})
            
            return response
            
        except Exception as e:
            logger.error(f"AI chat error: {e}")
            return {'status': 'error', 'message': 'An error occurred.', 'error': str(e)}

    def _build_prompt(self, user_message: str, context: Optional[Dict] = None) -> str:
        """Build prompt with context"""
        prompt_parts = [self.system_prompt, "\n\n"]
        
        # Add context if provided
        if context:
            prompt_parts.append("Context:\n")
            if 'predictions' in context:
                prompt_parts.append(f"Predictions: {json.dumps(context['predictions'], indent=2)}\n")
            if 'statistics' in context:
                prompt_parts.append(f"Statistics: {json.dumps(context['statistics'], indent=2)}\n")
            if 'betting_tips' in context:
                prompt_parts.append(f"Betting Tips: {json.dumps(context['betting_tips'], indent=2)}\n")
            prompt_parts.append("\n")
        
        # Add conversation history
        if self.conversation_history:
            prompt_parts.append("Conversation History:\n")
            for msg in self.conversation_history[-6:]:
                role = "User" if msg['role'] == 'user' else "Assistant"
                prompt_parts.append(f"{role}: {msg['content']}\n")
            prompt_parts.append("\n")
        
        # Add current user message
        prompt_parts.append(f"User: {user_message}\n")
        prompt_parts.append("Assistant:")
        
        return ''.join(prompt_parts)

    def _call_openai(self, user_message: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """Call OpenAI API"""
        try:
            url = "https://api.openai.com/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.openai_key}",
                "Content-Type": "application/json"
            }
            
            # Construct messages with system prompt
            messages = [{"role": "system", "content": self.system_prompt}]
            
            # Add context as a system note if present
            if context:
                context_str = json.dumps(context, indent=2)
                messages.append({"role": "system", "content": f"Current Context:\n{context_str}"})
                
            # Add history (excluding the user message we just added to self.history for generic prompt building)
            # Actually, let's just rebuild valid history for OpenAI
            for msg in self.conversation_history:
                 messages.append({"role": msg['role'], "content": msg['content']})
            
            payload = {
                "model": self.model_name if self.model_name != 'qwen2.5:7b' else "gpt-3.5-turbo",
                "messages": messages,
                "temperature": 0.7
            }
            
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            
            if response.status_code == 200:
                content = response.json()['choices'][0]['message']['content']
                return {'status': 'success', 'message': content, 'model': 'openai'}
            else:
                return {'status': 'error', 'message': f"OpenAI Error: {response.text}"}
                
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def _call_gemini(self, prompt: str) -> Dict[str, Any]:
        """Call Google Gemini API"""
        try:
            # Simple content generation endpoint
            model = self.model_name if self.model_name != 'qwen2.5:7b' else "gemini-1.5-flash"
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self.gemini_key}"
            
            payload = {
                "contents": [{
                    "parts": [{"text": prompt}]
                }]
            }
            
            response = requests.post(url, json=payload, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                if 'candidates' in data and data['candidates']:
                    content = data['candidates'][0]['content']['parts'][0]['text']
                    return {'status': 'success', 'message': content, 'model': 'gemini'}
                else:
                    return {'status': 'error', 'message': "No response from Gemini"}
            else:
                return {'status': 'error', 'message': f"Gemini Error: {response.text}"}
                
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def _call_ollama(self, prompt: str) -> Dict[str, Any]:
        """Call Ollama API"""
        try:
            url = f"{self.ollama_url}/api/generate"
            
            payload = {
                'model': self.model_name,
                'prompt': prompt,
                'stream': False,
                'options': {
                    'temperature': 0.7,
                    'top_p': 0.9,
                    'max_tokens': 500
                }
            }
            
            logger.info(f"Calling Ollama API: {url}")
            
            response = requests.post(url, json=payload, timeout=60)
            
            if response.status_code == 200:
                result = response.json()
                return {
                    'status': 'success',
                    'message': result['response'].strip(),
                    'model': self.model_name,
                    'timestamp': datetime.utcnow().isoformat()
                }
            else:
                return {
                    'status': 'error',
                    'message': 'Failed to generate response',
                    'error_code': response.status_code
                }
                
        except Exception as e:
            return {
                'status': 'error',
                'message': 'Failed to connect to AI service',
                'error': str(e)
            }

    def get_prediction_explanation(self, 
                                   home_team: str,
                                   away_team: str,
                                   predictions: Dict[str, Any]) -> str:
        """Get AI explanation of predictions"""
        context = {
            'predictions': predictions,
            'match': f"{home_team} vs {away_team}"
        }
        
        question = f"Explain the prediction for {home_team} vs {away_team} in simple terms. What are the key insights?"
        
        response = self.generate_response(question, context)
        
        if response['status'] == 'success':
            return response['message']
        else:
            return "Unable to generate explanation at this time."
    
    def get_betting_advice(self,
                          betting_tips: List[Dict[str, Any]]) -> str:
        """Get AI betting advice"""
        context = {
            'betting_tips': betting_tips
        }
        
        question = "Based on these betting tips, what would you recommend? Focus on the best value bets."
        
        response = self.generate_response(question, context)
        
        if response['status'] == 'success':
            return response['message']
        else:
            return "Unable to generate betting advice at this time."
    
    def clear_history(self):
        """Clear conversation history"""
        self.conversation_history = []
        logger.info("Conversation history cleared")


# Global instance
_ai_assistant = None


def get_ai_assistant(model_name: str = "qwen2.5:7b") -> FootballAIChatAssistant:
    """Get or create AI assistant (singleton)"""
    global _ai_assistant
    
    if _ai_assistant is None:
        _ai_assistant = FootballAIChatAssistant() # No args, uses env vars
        # If model_name passed (legacy), we ignore it in favor of env vars or defaults
        logger.info(f"AI assistant initialized via factory")
    
    return _ai_assistant


# Fallback responses when AI is not available
FALLBACK_RESPONSES = {
    'prediction': "I can help explain predictions! Our system uses Bayesian inference to analyze team form, head-to-head records, and goal statistics to generate accurate predictions.",
    'betting': "For betting tips, look for high confidence predictions (70%+) with low risk. Value bets are highlighted with star ratings.",
    'statistics': "Check the Statistics dashboard for comprehensive team analysis including form, H2H records, and venue performance.",
    'help': "I can help you with:\n- Understanding predictions\n- Betting tips and advice\n- Team statistics\n- Match analysis\n\nJust ask me anything about football predictions!"
}


def get_fallback_response(query: str) -> str:
    """Get fallback response when AI is not available"""
    query_lower = query.lower()
    
    if 'predict' in query_lower or 'forecast' in query_lower:
        return FALLBACK_RESPONSES['prediction']
    elif 'bet' in query_lower or 'tip' in query_lower:
        return FALLBACK_RESPONSES['betting']
    elif 'stat' in query_lower or 'form' in query_lower:
        return FALLBACK_RESPONSES['statistics']
    else:
        return FALLBACK_RESPONSES['help']

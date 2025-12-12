/**
 * GenUI Renderer Component for React Native
 *
 * Renders generated HTML/CSS/JS UIs in a sandboxed WebView with
 * native data bridge integration.
 */

import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  StyleSheet,
  View,
  ActivityIndicator,
  Text,
  TouchableOpacity,
} from 'react-native';
import { WebView, WebViewMessageEvent } from 'react-native-webview';

// Types
interface DataRequest {
  id: string;
  endpoint: string;
  params?: Record<string, any>;
}

interface GenUIRendererProps {
  /** Generation ID to render */
  generationId: string;
  /** Generated HTML content */
  html?: string;
  /** Callback to handle data requests from the WebView */
  onDataRequest?: (endpoint: string, params?: Record<string, any>) => Promise<any>;
  /** Callback for user interactions */
  onInteraction?: (event: InteractionEvent) => void;
  /** Callback for errors */
  onError?: (error: Error) => void;
  /** Loading state */
  loading?: boolean;
  /** Custom styles */
  style?: object;
  /** Enable debug mode */
  debug?: boolean;
}

interface InteractionEvent {
  type: string;
  component?: string;
  data?: any;
  timestamp: number;
}

/**
 * Bridge script injected into WebView for native communication
 */
const DATA_BRIDGE_SCRIPT = `
  (function() {
    // Store pending requests
    const pendingRequests = new Map();
    let requestId = 0;

    // Create the OPTIX Data Bridge
    window.OPTIXDataBridge = {
      // Request data from native side
      request: function(endpoint, params) {
        return new Promise((resolve, reject) => {
          const id = 'req_' + (++requestId);
          pendingRequests.set(id, { resolve, reject });

          window.ReactNativeWebView.postMessage(JSON.stringify({
            type: 'data_request',
            id: id,
            endpoint: endpoint,
            params: params || {}
          }));

          // Timeout after 30 seconds
          setTimeout(() => {
            if (pendingRequests.has(id)) {
              pendingRequests.delete(id);
              reject(new Error('Request timeout'));
            }
          }, 30000);
        });
      },

      // Subscribe to data channel
      subscribe: function(channel, callback) {
        if (!window._subscriptions) {
          window._subscriptions = new Map();
        }
        if (!window._subscriptions.has(channel)) {
          window._subscriptions.set(channel, []);
        }
        window._subscriptions.get(channel).push(callback);

        window.ReactNativeWebView.postMessage(JSON.stringify({
          type: 'subscribe',
          channel: channel
        }));
      },

      // Unsubscribe from data channel
      unsubscribe: function(channel, callback) {
        if (window._subscriptions && window._subscriptions.has(channel)) {
          const callbacks = window._subscriptions.get(channel);
          const index = callbacks.indexOf(callback);
          if (index > -1) {
            callbacks.splice(index, 1);
          }

          if (callbacks.length === 0) {
            window.ReactNativeWebView.postMessage(JSON.stringify({
              type: 'unsubscribe',
              channel: channel
            }));
          }
        }
      }
    };

    // Handle messages from native side
    window.handleNativeMessage = function(message) {
      const data = JSON.parse(message);

      if (data.type === 'data_response') {
        const pending = pendingRequests.get(data.id);
        if (pending) {
          pendingRequests.delete(data.id);
          if (data.error) {
            pending.reject(new Error(data.error));
          } else {
            pending.resolve(data.data);
          }
        }
      } else if (data.type === 'data_update') {
        if (window._subscriptions && window._subscriptions.has(data.channel)) {
          const callbacks = window._subscriptions.get(data.channel);
          callbacks.forEach(cb => {
            try {
              cb(data.data);
            } catch (e) {
              console.error('Subscription callback error:', e);
            }
          });
        }
      }
    };

    // Track user interactions
    document.addEventListener('click', function(e) {
      window.ReactNativeWebView.postMessage(JSON.stringify({
        type: 'interaction',
        event: 'click',
        target: e.target.tagName,
        component: e.target.closest('[data-component]')?.dataset?.component,
        timestamp: Date.now()
      }));
    });

    // Signal bridge is ready
    window.ReactNativeWebView.postMessage(JSON.stringify({
      type: 'bridge_ready'
    }));
  })();
`;

/**
 * GenUIRenderer Component
 *
 * Renders generated UIs in a sandboxed WebView with native data bridge.
 */
export const GenUIRenderer: React.FC<GenUIRendererProps> = ({
  generationId,
  html,
  onDataRequest,
  onInteraction,
  onError,
  loading = false,
  style,
  debug = false,
}) => {
  const webViewRef = useRef<WebView>(null);
  const [bridgeReady, setBridgeReady] = useState(false);
  const [webViewError, setWebViewError] = useState<string | null>(null);

  // Handle messages from WebView
  const handleMessage = useCallback(async (event: WebViewMessageEvent) => {
    try {
      const message = JSON.parse(event.nativeEvent.data);

      switch (message.type) {
        case 'bridge_ready':
          setBridgeReady(true);
          break;

        case 'data_request':
          if (onDataRequest) {
            try {
              const data = await onDataRequest(message.endpoint, message.params);
              webViewRef.current?.injectJavaScript(`
                window.handleNativeMessage('${JSON.stringify({
                  type: 'data_response',
                  id: message.id,
                  data: data,
                })}');
                true;
              `);
            } catch (error: any) {
              webViewRef.current?.injectJavaScript(`
                window.handleNativeMessage('${JSON.stringify({
                  type: 'data_response',
                  id: message.id,
                  error: error.message,
                })}');
                true;
              `);
            }
          }
          break;

        case 'subscribe':
          // Handle subscription - connect to real-time data source
          if (debug) {
            console.log('Subscribe:', message.channel);
          }
          break;

        case 'unsubscribe':
          // Handle unsubscription
          if (debug) {
            console.log('Unsubscribe:', message.channel);
          }
          break;

        case 'interaction':
          if (onInteraction) {
            onInteraction({
              type: message.event,
              component: message.component,
              data: message,
              timestamp: message.timestamp,
            });
          }
          break;

        default:
          if (debug) {
            console.log('Unknown message type:', message.type);
          }
      }
    } catch (error: any) {
      if (debug) {
        console.error('Message parse error:', error);
      }
    }
  }, [onDataRequest, onInteraction, debug]);

  // Handle WebView errors
  const handleError = useCallback((syntheticEvent: any) => {
    const { nativeEvent } = syntheticEvent;
    setWebViewError(nativeEvent.description || 'WebView error');
    if (onError) {
      onError(new Error(nativeEvent.description));
    }
  }, [onError]);

  // Inject data into WebView
  const injectData = useCallback((channel: string, data: any) => {
    if (webViewRef.current && bridgeReady) {
      webViewRef.current.injectJavaScript(`
        window.handleNativeMessage('${JSON.stringify({
          type: 'data_update',
          channel: channel,
          data: data,
        })}');
        true;
      `);
    }
  }, [bridgeReady]);

  // Render loading state
  if (loading) {
    return (
      <View style={[styles.container, styles.centered, style]}>
        <ActivityIndicator size="large" color="#2563EB" />
        <Text style={styles.loadingText}>Generating UI...</Text>
      </View>
    );
  }

  // Render error state
  if (webViewError) {
    return (
      <View style={[styles.container, styles.centered, style]}>
        <Text style={styles.errorIcon}>⚠️</Text>
        <Text style={styles.errorText}>{webViewError}</Text>
        <TouchableOpacity
          style={styles.retryButton}
          onPress={() => setWebViewError(null)}
        >
          <Text style={styles.retryButtonText}>Retry</Text>
        </TouchableOpacity>
      </View>
    );
  }

  // Render empty state
  if (!html) {
    return (
      <View style={[styles.container, styles.centered, style]}>
        <Text style={styles.emptyText}>No UI generated</Text>
      </View>
    );
  }

  return (
    <View style={[styles.container, style]}>
      <WebView
        ref={webViewRef}
        source={{ html }}
        style={styles.webView}
        originWhitelist={['*']}
        onMessage={handleMessage}
        onError={handleError}
        injectedJavaScript={DATA_BRIDGE_SCRIPT}
        javaScriptEnabled={true}
        domStorageEnabled={false}
        allowFileAccess={false}
        allowUniversalAccessFromFileURLs={false}
        mixedContentMode="never"
        cacheEnabled={false}
        incognito={true}
        scrollEnabled={true}
        bounces={false}
        showsHorizontalScrollIndicator={false}
        showsVerticalScrollIndicator={true}
        contentInsetAdjustmentBehavior="automatic"
        decelerationRate="normal"
      />
      {debug && (
        <View style={styles.debugBadge}>
          <Text style={styles.debugText}>
            {bridgeReady ? '✓ Bridge Ready' : '... Connecting'}
          </Text>
        </View>
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0F172A',
  },
  centered: {
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  webView: {
    flex: 1,
    backgroundColor: 'transparent',
  },
  loadingText: {
    marginTop: 12,
    color: '#94A3B8',
    fontSize: 14,
  },
  errorIcon: {
    fontSize: 48,
    marginBottom: 12,
  },
  errorText: {
    color: '#EF4444',
    fontSize: 14,
    textAlign: 'center',
    marginBottom: 16,
  },
  retryButton: {
    backgroundColor: '#2563EB',
    paddingHorizontal: 24,
    paddingVertical: 12,
    borderRadius: 8,
  },
  retryButtonText: {
    color: '#FFFFFF',
    fontSize: 14,
    fontWeight: '600',
  },
  emptyText: {
    color: '#94A3B8',
    fontSize: 14,
  },
  debugBadge: {
    position: 'absolute',
    bottom: 8,
    right: 8,
    backgroundColor: 'rgba(0, 0, 0, 0.7)',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 4,
  },
  debugText: {
    color: '#22C55E',
    fontSize: 10,
  },
});

export default GenUIRenderer;

import { useState } from 'react';
import { useNotifications, useMarkNotificationRead, useMarkAllNotificationsRead, useNotificationConfig, useUpdateNotificationConfig, useTestWebhook } from '../../hooks/useNotifications';

interface NotificationPanelProps {
  isOpen: boolean;
  onClose: () => void;
}

export function NotificationPanel({ isOpen, onClose }: NotificationPanelProps) {
  const [showSettings, setShowSettings] = useState(false);
  const [webhookUrl, setWebhookUrl] = useState('');
  const [minSeverity, setMinSeverity] = useState('warning');
  const [isSaving, setIsSaving] = useState(false);
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null);

  const { data: notifications = [] } = useNotifications(50, false);
  const { data: config } = useNotificationConfig();
  const { mutate: markAsRead } = useMarkNotificationRead();
  const { mutate: markAllAsRead } = useMarkAllNotificationsRead();
  const { mutate: updateConfig } = useUpdateNotificationConfig();
  const { mutate: testWebhook } = useTestWebhook();

  if (!isOpen) return null;

  // Initialize form with current config
  const initialWebhookUrl = config?.webhookUrl || '';
  const initialMinSeverity = config?.minSeverity || 'warning';

  const handleSaveSettings = async () => {
    setIsSaving(true);
    try {
      updateConfig(
        {
          webhookUrl: webhookUrl || undefined,
          minSeverity: minSeverity,
        },
        {
          onSuccess: () => {
            setIsSaving(false);
            setShowSettings(false);
          },
        }
      );
    } catch (error) {
      console.error('Error saving settings:', error);
      setIsSaving(false);
    }
  };

  const handleTestWebhook = async () => {
    if (!webhookUrl) return;
    testWebhook(webhookUrl, {
      onSuccess: (result) => {
        setTestResult(result);
      },
    });
  };

  const severityColors: Record<string, string> = {
    critical: 'text-red-400',
    warning: 'text-yellow-400',
    info: 'text-blue-400',
  };

  const severityBgColors: Record<string, string> = {
    critical: 'bg-red-500/10',
    warning: 'bg-yellow-500/10',
    info: 'bg-blue-500/10',
  };

  const getTimeAgo = (createdAt: string): string => {
    const date = new Date(createdAt);
    const now = new Date();
    const seconds = Math.floor((now.getTime() - date.getTime()) / 1000);

    if (seconds < 60) return 'just now';
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
    return `${Math.floor(seconds / 86400)}d ago`;
  };

  return (
    <div className="fixed inset-0 z-50 pointer-events-none">
      {/* Overlay to close on click outside */}
      <div
        className="absolute inset-0 pointer-events-auto"
        onClick={onClose}
      />

      {/* Panel */}
      <div className="absolute top-16 right-4 w-96 bg-[#0a0a0a] border border-neutral-800 rounded-lg shadow-2xl pointer-events-auto flex flex-col max-h-[80vh] z-10">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-neutral-800">
          <h2 className="text-lg font-semibold text-neutral-100">
            {showSettings ? 'Settings' : 'Notifications'}
          </h2>
          <button
            onClick={onClose}
            className="text-neutral-500 hover:text-neutral-300 transition-colors"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto">
          {!showSettings ? (
            <>
              {/* Mark All Read Button */}
              {notifications.length > 0 && (
                <div className="p-3 border-b border-neutral-800">
                  <button
                    onClick={() => markAllAsRead()}
                    className="w-full px-3 py-2 bg-neutral-800 hover:bg-neutral-700 text-neutral-100 text-sm rounded transition-colors"
                  >
                    Mark All as Read
                  </button>
                </div>
              )}

              {/* Notifications List */}
              {notifications.length === 0 ? (
                <div className="p-8 text-center">
                  <p className="text-neutral-500">No notifications</p>
                </div>
              ) : (
                <div className="divide-y divide-neutral-800">
                  {notifications.map((notif) => (
                    <div
                      key={notif.id}
                      onClick={() => {
                        if (!notif.read) {
                          markAsRead(notif.id);
                        }
                      }}
                      className={`p-4 cursor-pointer transition-colors ${
                        notif.read
                          ? 'bg-[#0a0a0a]'
                          : 'bg-neutral-900/50 hover:bg-neutral-800/50'
                      }`}
                    >
                      <div className="flex gap-3">
                        {/* Severity Dot */}
                        <div className="flex-shrink-0 mt-1">
                          <div
                            className={`w-2 h-2 rounded-full ${
                              notif.severity === 'critical'
                                ? 'bg-red-500'
                                : notif.severity === 'warning'
                                ? 'bg-yellow-500'
                                : 'bg-blue-500'
                            }`}
                          />
                        </div>

                        {/* Content */}
                        <div className="flex-1 min-w-0">
                          <div className="flex items-start justify-between gap-2">
                            <h3 className="text-sm font-semibold text-neutral-100 line-clamp-1">
                              {notif.title}
                            </h3>
                            {notif.ticker && (
                              <span className="flex-shrink-0 text-xs font-mono text-neutral-400 bg-neutral-800 px-2 py-1 rounded">
                                {notif.ticker}
                              </span>
                            )}
                          </div>
                          <p className="text-xs text-neutral-400 mt-1 line-clamp-2">
                            {notif.body}
                          </p>
                          <div className="flex items-center gap-2 mt-2">
                            <span className="text-xs text-neutral-500">
                              {getTimeAgo(notif.createdAt)}
                            </span>
                            <span className={`text-xs font-medium ${severityColors[notif.severity]}`}>
                              {notif.severity.charAt(0).toUpperCase() + notif.severity.slice(1)}
                            </span>
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </>
          ) : (
            /* Settings Panel */
            <div className="p-4 space-y-4">
              {/* Webhook URL */}
              <div>
                <label className="block text-sm font-medium text-neutral-300 mb-2">
                  Webhook URL
                </label>
                <input
                  type="text"
                  value={webhookUrl || initialWebhookUrl}
                  onChange={(e) => setWebhookUrl(e.target.value)}
                  placeholder="https://example.com/webhook"
                  className="w-full px-3 py-2 bg-neutral-800 border border-neutral-700 rounded text-neutral-100 placeholder-neutral-600 focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
                />
              </div>

              {/* Min Severity */}
              <div>
                <label className="block text-sm font-medium text-neutral-300 mb-2">
                  Minimum Severity
                </label>
                <select
                  value={minSeverity || initialMinSeverity}
                  onChange={(e) => setMinSeverity(e.target.value)}
                  className="w-full px-3 py-2 bg-neutral-800 border border-neutral-700 rounded text-neutral-100 focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
                >
                  <option value="info">Info</option>
                  <option value="warning">Warning</option>
                  <option value="critical">Critical</option>
                </select>
              </div>

              {/* Test Webhook Button */}
              {(webhookUrl || initialWebhookUrl) && (
                <button
                  onClick={handleTestWebhook}
                  className="w-full px-3 py-2 bg-neutral-800 hover:bg-neutral-700 text-neutral-100 text-sm rounded transition-colors"
                >
                  Test Webhook
                </button>
              )}

              {/* Test Result */}
              {testResult && (
                <div
                  className={`p-3 rounded text-sm ${
                    testResult.success
                      ? 'bg-green-500/10 text-green-400 border border-green-500/20'
                      : 'bg-red-500/10 text-red-400 border border-red-500/20'
                  }`}
                >
                  {testResult.message}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between p-4 border-t border-neutral-800 gap-2">
          <button
            onClick={() => {
              setShowSettings(!showSettings);
              setTestResult(null);
            }}
            className="px-3 py-2 bg-neutral-800 hover:bg-neutral-700 text-neutral-100 text-sm rounded transition-colors"
          >
            {showSettings ? 'Back' : 'Settings'}
          </button>
          {showSettings && (
            <button
              onClick={handleSaveSettings}
              disabled={isSaving}
              className="px-3 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-neutral-600 text-white text-sm rounded transition-colors"
            >
              {isSaving ? 'Saving...' : 'Save'}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

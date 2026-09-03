import { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Link } from 'react-router-dom';

import { Alert, EmptyState, ErrorState, LoadingState } from '../../components/Feedback';
import StatusChip from '../../components/StatusChip';
import { fetchNotifications, markAllRead, markRead } from './notificationApi';
import { categoryLabel, isUrgent, relativeTime, targetPath } from './notificationFormat';

export default function NotificationsPage() {
  const navigate = useNavigate();
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [unreadOnly, setUnreadOnly] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [banner, setBanner] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const data = await fetchNotifications({ unread_only: unreadOnly });
      setNotifications(data.notifications);
      setUnreadCount(data.unread_count);
    } catch (apiError) {
      setError(apiError.message);
    } finally {
      setLoading(false);
    }
  }, [unreadOnly]);

  useEffect(() => {
    load();
  }, [load]);

  const openNotification = async (notification) => {
    try {
      if (!notification.is_read) await markRead(notification.id);
      const path = targetPath(notification);
      if (path) navigate(path);
      else await load();
    } catch (apiError) {
      setError(apiError.message);
    }
  };

  const clearAll = async () => {
    try {
      const result = await markAllRead();
      setBanner(`Marked ${result.marked} notification${result.marked === 1 ? '' : 's'} as read.`);
      await load();
    } catch (apiError) {
      setError(apiError.message);
    }
  };

  if (loading) return <LoadingState message="Loading your notifications..." />;
  if (error && notifications.length === 0) return <ErrorState message={error} onRetry={load} />;

  return (
    <>
      <div className="ju-page-header">
        <h1>Notifications</h1>
        <p>{unreadCount === 0 ? 'You are all caught up.' : `${unreadCount} unread notification${unreadCount === 1 ? '' : 's'}.`}</p>
      </div>
      <Alert tone="success">{banner}</Alert>
      <Alert tone="error">{error}</Alert>
      <div className="ju-card">
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: 'var(--ju-space-3)', flexWrap: 'wrap', marginBottom: 'var(--ju-space-4)' }}>
          <div style={{ display: 'flex', gap: 'var(--ju-space-2)' }}>
            <button type="button" className={`ju-btn ${unreadOnly ? 'ju-btn--secondary' : 'ju-btn--primary'}`} onClick={() => setUnreadOnly(false)}>All</button>
            <button type="button" className={`ju-btn ${unreadOnly ? 'ju-btn--primary' : 'ju-btn--secondary'}`} onClick={() => setUnreadOnly(true)}>Unread</button>
          </div>
          <div style={{ display: 'flex', gap: 'var(--ju-space-2)' }}>
            <Link to="/notifications/preferences" className="ju-btn ju-btn--secondary">Preferences</Link>
            <button type="button" className="ju-btn ju-btn--secondary" onClick={clearAll} disabled={unreadCount === 0}>Mark All Read</button>
          </div>
        </div>
        {notifications.length === 0 ? (
          <EmptyState title={unreadOnly ? 'Nothing unread' : 'No notifications yet'} hint="Appointment reminders and updates will appear here." />
        ) : (
          <ul style={{ listStyle: 'none', margin: 0, padding: 0, display: 'grid', gap: 'var(--ju-space-2)' }}>
            {notifications.map((notification) => (
              <li key={notification.id}>
                <button type="button" onClick={() => openNotification(notification)} style={{ width: '100%', textAlign: 'left', cursor: 'pointer', border: '1px solid var(--ju-border)', borderLeft: `4px solid ${notification.is_read ? 'var(--ju-border)' : 'var(--ju-primary)'}`, borderRadius: 'var(--ju-radius)', padding: 'var(--ju-space-4)', background: notification.is_read ? 'var(--ju-surface)' : '#f0fdfa', font: 'inherit', color: 'inherit', minHeight: 'var(--ju-touch-target)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', gap: 'var(--ju-space-3)', flexWrap: 'wrap', alignItems: 'center' }}>
                    <strong>{notification.title}</strong>
                    <span style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                      {isUrgent(notification.category) && <StatusChip status="error" label={categoryLabel(notification.category)} />}
                      {!notification.is_read && <StatusChip status="info" label="New" />}
                      <span className="ju-field__help">{relativeTime(notification.created_at)}</span>
                    </span>
                  </div>
                  <p style={{ margin: '6px 0 0' }}>{notification.body}</p>
                  {!isUrgent(notification.category) && <p className="ju-field__help" style={{ margin: '4px 0 0' }}>{categoryLabel(notification.category)}</p>}
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </>
  );
}

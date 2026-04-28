/**
 * 浏览器通知工具 - 增强版
 */

// 记录已通知的任务，避免重复通知
let notifiedTaskIds = new Set<number>()
let notificationPollingInterval: number | null = null
let notificationCheckInterval = 60000 // 默认每分钟检查一次

export const notify = (title: string, options?: NotificationOptions) => {
  if (!('Notification' in window)) {
    console.warn('此浏览器不支持桌面通知');
    return;
  }

  if (Notification.permission === 'granted') {
    const notification = new Notification(title, options);
    
    // 添加点击事件
    notification.onclick = () => {
      window.focus();
      notification.close();
    };
    
    return notification;
  } else if (Notification.permission !== 'denied') {
    Notification.requestPermission().then((permission) => {
      if (permission === 'granted') {
        const notification = new Notification(title, options);
        notification.onclick = () => {
          window.focus();
          notification.close();
        };
        return notification;
      }
    });
  }
};

// 任务提醒专用
export const notifyTask = (task: any) => {
  if (notifiedTaskIds.has(task.id)) {
    return;
  }

  notifiedTaskIds.add(task.id);
  
  const priorityColors = {
    '高': '🔴',
    '中': '🟠',
    '低': '🟢'
  } as Record<string, string>;
  
  const priorityEmoji = priorityColors[task.priority] || '⚪';
  
  notify(`${priorityEmoji} 任务提醒：${task.raw_task || task.task}`, {
    body: `截止日期：${task.deadline}\n优先级：${task.priority}\n分类：${task.category || '未分类'}`,
    icon: '/favicon.ico',
    tag: `task-${task.id}`
  });
};

// 清除已通知的记录（用于刷新）
export const clearNotifiedTasks = () => {
  notifiedTaskIds.clear();
};

// 设置检查间隔（毫秒）
export const setNotificationCheckInterval = (interval: number) => {
  notificationCheckInterval = interval;
  if (notificationPollingInterval) {
    stopNotificationPolling();
  }
};

// 开始轮询检查任务
export const startNotificationPolling = (checkCallback: () => Promise<any[]>) => {
  if (notificationPollingInterval) {
    return;
  }

  // 立即执行一次
  checkCallback().then(tasks => {
    tasks.forEach(task => notifyTask(task));
  });

  // 设置轮询
  notificationPollingInterval = window.setInterval(() => {
    checkCallback().then(tasks => {
      tasks.forEach(task => notifyTask(task));
    });
  }, notificationCheckInterval);
};

// 停止轮询
export const stopNotificationPolling = () => {
  if (notificationPollingInterval) {
    window.clearInterval(notificationPollingInterval);
    notificationPollingInterval = null;
  }
};

// 请求通知权限
export const requestNotificationPermission = async (): Promise<boolean> => {
  if (!('Notification' in window)) {
    return false;
  }

  if (Notification.permission === 'granted') {
    return true;
  }

  if (Notification.permission === 'denied') {
    console.warn('通知权限已被拒绝，请在浏览器设置中开启');
    return false;
  }

  const permission = await Notification.requestPermission();
  return permission === 'granted';
};

// 检查是否已获得通知权限
export const hasNotificationPermission = (): boolean => {
  return 'Notification' in window && Notification.permission === 'granted';
};

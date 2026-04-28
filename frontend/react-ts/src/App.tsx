import { useMemo, useState, useEffect } from 'react'
import { Layout, Menu, Typography, Badge, Avatar, Button, Space, Dropdown, Popover, List, Card, Tag, Drawer, FloatButton } from 'antd'
import TaskList from './components/TaskList'
import CalendarView from './components/CalendarView'
import Dashboard from './components/Dashboard'
import CreateTask from './components/CreateTask'
import ChatComponent from './components/ChatComponent'
import CategoryManagement from './components/CategoryManagement'
import TaskTemplateManagement from './components/TaskTemplateManagement'
import KnowledgeBase from './components/KnowledgeBase'
import AuthModal from './components/AuthModal'
import SettingsPage from './components/SettingsPage'
import {
  CheckCircleOutlined,
  CalendarOutlined,
  DashboardOutlined,
  PlusOutlined,
  BellOutlined,
  StarFilled,
  MessageOutlined,
  UserOutlined,
  TagsOutlined,
  LogoutOutlined,
  SettingOutlined,
  SaveOutlined,
  FileTextOutlined,
  ClockCircleOutlined,
  CloseOutlined,
  MenuOutlined
} from '@ant-design/icons'
import { useTaskStore } from './store/taskStore'
import { useAuthStore } from './store/authStore'
import { notify, startNotificationPolling, stopNotificationPolling, requestNotificationPermission, hasNotificationPermission, clearNotifiedTasks, notifyTask } from './utils/notification'

const { Header, Content, Sider } = Layout
const { Title, Text } = Typography

function App() {
  const [current, setCurrent] = useState('dashboard')
  const [authModalVisible, setAuthModalVisible] = useState(false)
  const [notificationsOpen, setNotificationsOpen] = useState(false)
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const [isMobile, setIsMobile] = useState(false)
  const { todayTasks, fetchTasks, fetchTodayTasks, tasks } = useTaskStore()
  const { isAuthenticated, user, logout, initAuth } = useAuthStore()

  // 检测移动端
  useEffect(() => {
    const checkIsMobile = () => {
      setIsMobile(window.innerWidth < 768)
    }
    
    checkIsMobile()
    window.addEventListener('resize', checkIsMobile)
    
    return () => {
      window.removeEventListener('resize', checkIsMobile)
    }
  }, [])

  useEffect(() => {
    initAuth()
  }, [initAuth])

  useEffect(() => {
    if (isAuthenticated) {
      fetchTasks()
      fetchTodayTasks()
      
      // 清除之前的通知记录
      clearNotifiedTasks()
    }
  }, [isAuthenticated, fetchTasks, fetchTodayTasks])
  
  // 请求通知权限
  useEffect(() => {
    if ('Notification' in window && Notification.permission === 'default') {
      requestNotificationPermission()
    }
  }, [])

  // 开始/停止通知轮询
  useEffect(() => {
    if (isAuthenticated && hasNotificationPermission()) {
      const checkTasks = async () => {
        // 检查即将到期的任务（这里先简单检查今天的任务）
        await fetchTodayTasks()
        return todayTasks.filter(task => {
          // 检查是否在未来30分钟内到期的任务（简化逻辑）
          return task
        })
      }
      
      startNotificationPolling(checkTasks)
    } else {
      stopNotificationPolling()
    }

    return () => {
      stopNotificationPolling()
    }
  }, [isAuthenticated, todayTasks])

  // 新增任务时通知
  useEffect(() => {
    if (isAuthenticated && tasks.length > 0) {
      // 简单处理：只通知最新添加的任务（如果有）
      const latestTask = tasks[tasks.length - 1]
      if (latestTask) {
        // 这里可以添加逻辑判断是否需要立即通知新任务
      }
    }
  }, [tasks.length, isAuthenticated])

  const handleMenuClick = (e: any) => {
    if (!isAuthenticated && ['tasks', 'calendar', 'create', 'categories', 'chat', 'templates', 'knowledge'].includes(e.key)) {
      setAuthModalVisible(true)
      return
    }
    setCurrent(e.key)
    if (isMobile) {
      setMobileMenuOpen(false)
    }
  }

  const handleEnableNotifications = async () => {
    const granted = await requestNotificationPermission()
    if (granted) {
      notify('通知已开启', {
        body: '您将收到任务到期提醒。',
        icon: '/favicon.ico'
      })
    }
  }

  const handleLogout = () => {
    logout()
    setCurrent('dashboard')
  }

  const userMenuItems = [
    {
      key: 'profile',
      icon: <UserOutlined />,
      label: '个人中心'
    },
    {
      key: 'settings',
      icon: <SettingOutlined />,
      label: '设置'
    },
    {
      key: 'logout',
      icon: <LogoutOutlined />,
      label: '退出登录'
    }
  ]

  const handleUserMenuClick = (e: any) => {
    if (e.key === 'logout') {
      handleLogout()
    } else if (e.key === 'settings') {
      setCurrent('settings')
    } else if (e.key === 'profile') {
      setCurrent('dashboard')
    }
  }

  // 通知弹窗内容
  const notificationContent = (
    <div style={{ width: 350, padding: '8px 0' }}>
      <div style={{ padding: '0 12px 12px', borderBottom: '1px solid #f0f0f0', marginBottom: 8 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Text strong>今日任务提醒</Text>
          {!hasNotificationPermission() && (
            <Button type="link" size="small" onClick={handleEnableNotifications}>
              开启通知
            </Button>
          )}
        </div>
      </div>
      
      {todayTasks.length > 0 ? (
        <List
          dataSource={todayTasks}
          renderItem={(task) => (
            <List.Item style={{ padding: '8px 12px' }}>
              <List.Item.Meta
                avatar={<ClockCircleOutlined style={{ color: task.priority === '高' ? '#ff4d4f' : task.priority === '中' ? '#faad14' : '#52c41a' }} />}
                title={
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <Text ellipsis style={{ maxWidth: 200 }} strong>{task.raw_task || task.task}</Text>
                    <Tag color={task.priority === '高' ? 'red' : task.priority === '中' ? 'orange' : 'green'}>
                      {task.priority}
                    </Tag>
                  </div>
                }
                description={
                  <Space size="small">
                    <Text type="secondary" style={{ fontSize: '12px' }}>
                      <ClockCircleOutlined /> {task.deadline}
                    </Text>
                    {task.category && (
                      <Tag size="small">{task.category}</Tag>
                    )}
                  </Space>
                }
              />
            </List.Item>
          )}
        />
      ) : (
        <div style={{ padding: '24px 12px', textAlign: 'center' }}>
          <Text type="secondary">
            今天没有需要特别关注的任务 😊
          </Text>
        </div>
      )}
      
      <div style={{ padding: '8px 12px', borderTop: '1px solid #f0f0f0', marginTop: 8 }}>
        <Button type="link" size="small" onClick={() => {
          setCurrent('tasks')
          setNotificationsOpen(false)
        }} style={{ width: '100%', textAlign: 'center' }}>
          查看全部任务
        </Button>
      </div>
    </div>
  )

  const menuItems = useMemo(
    () => [
      {
        key: 'dashboard',
        icon: <DashboardOutlined />,
        label: '仪表盘'
      },
      {
        key: 'tasks',
        icon: <CheckCircleOutlined />,
        label: '任务列表'
      },
      {
        key: 'calendar',
        icon: <CalendarOutlined />,
        label: '日历视图'
      },
      {
        key: 'create',
        icon: <PlusOutlined />,
        label: '创建任务'
      },
      {
                key: 'categories',
                icon: <TagsOutlined />,
                label: '分类管理'
            },
            {
                key: 'templates',
                icon: <SaveOutlined />,
                label: '任务模板'
            },
            {
                key: 'chat',
                icon: <MessageOutlined />,
                label: '智能助手'
            },
            {
                key: 'knowledge',
                icon: <FileTextOutlined />,
                label: '知识库管理'
            }
    ],
    []
  )

  const currentTitle = useMemo(() => {
    const titleMap: Record<string, string> = {
      dashboard: '掌控今天的重点事项',
      tasks: '清晰整理全部任务与进度',
      calendar: '把任务放进时间安排里',
      create: '快速用自然语言生成任务',
      categories: '管理任务分类体系',
      templates: '管理任务模板',
      chat: '与 AI 助手深度交流',
      knowledge: '管理知识库内容'
    }

    return titleMap[current] || titleMap.dashboard
  }, [current])

  const renderContent = () => {
    switch (current) {
      case 'dashboard':
        return <Dashboard />
      case 'tasks':
        return <TaskList />
      case 'calendar':
        return <CalendarView />
      case 'create':
        return <CreateTask />
      case 'categories':
        return <CategoryManagement />
      case 'templates':
        return <TaskTemplateManagement />
      case 'chat':
        return <ChatComponent />
      case 'knowledge':
        return <KnowledgeBase />
      case 'settings':
        return <SettingsPage />
      default:
        return <Dashboard />
    }
  }

  return (
    <Layout className="app-shell">
      {/* 桌面端侧边栏 */}
      {!isMobile && (
        <Sider width={248} className="app-sider" breakpoint="lg" collapsedWidth="0">
          <div className="brand-panel">
            <div className="brand-icon">
              <StarFilled />
            </div>
            <div>
              <Text className="brand-kicker">Smart Planner</Text>
              <Title level={4} className="brand-title">
                智能记录中心
              </Title>
            </div>
          </div>
          <div className="sider-summary-card">
            <Text className="sider-summary-label">今日提醒</Text>
            <div className="sider-summary-value">{todayTasks.length}</div>
            <Text className="sider-summary-subtitle">
              {todayTasks.length > 0 ? '别忘了优先处理今天到期的事项' : '今天的节奏看起来很从容'}
            </Text>
          </div>
          <div className="sider-menu-wrapper">
            <Menu
              mode="inline"
              selectedKeys={[current]}
              className="app-menu"
              onClick={handleMenuClick}
              items={menuItems}
            />
          </div>
        </Sider>
      )}

      {/* 移动端抽屉导航 */}
      <Drawer
        title={
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div className="brand-icon" style={{ width: 32, height: 32, fontSize: 16 }}>
              <StarFilled />
            </div>
            <div>
              <Text style={{ fontSize: '12px', color: '#6b7280' }}>Smart Planner</Text>
              <Title level={5} style={{ margin: 0 }}>智能记录中心</Title>
            </div>
          </div>
        }
        placement="left"
        onClose={() => setMobileMenuOpen(false)}
        open={mobileMenuOpen}
        width={280}
        styles={{ body: { padding: 0 } }}
      >
        {isAuthenticated && (
          <div className="sider-summary-card" style={{ margin: '16px', borderRadius: 12 }}>
            <Text className="sider-summary-label">今日提醒</Text>
            <div className="sider-summary-value">{todayTasks.length}</div>
            <Text className="sider-summary-subtitle">
              {todayTasks.length > 0 ? '别忘了优先处理今天到期的事项' : '今天的节奏看起来很从容'}
            </Text>
          </div>
        )}
        <div className="sider-menu-wrapper">
          <Menu
            mode="inline"
            selectedKeys={[current]}
            className="app-menu"
            onClick={handleMenuClick}
            items={menuItems}
            style={{ borderRight: 0 }}
          />
        </div>
      </Drawer>

      <Layout className="app-main-layout">
        <Header className="app-header" style={{ paddingLeft: isMobile ? 16 : 24 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            {/* 移动端菜单按钮 */}
            {isMobile && (
              <Button
                type="text"
                icon={<MenuOutlined />}
                onClick={() => setMobileMenuOpen(true)}
                style={{ fontSize: 20 }}
              />
            )}
            <div>
              <Text className="page-kicker">智能待办与日程管理</Text>
              <Title level={isMobile ? 4 : 2} className="page-title">
                {currentTitle}
              </Title>
            </div>
          </div>
          <div className="header-right">
            <Space size="middle">
              {isAuthenticated && (
                <Popover
                  content={notificationContent}
                  title={null}
                  trigger="click"
                  open={notificationsOpen}
                  onOpenChange={setNotificationsOpen}
                  placement="bottomRight"
                >
                  <Badge count={todayTasks.length} offset={[-2, 2]}>
                    <Button
                      type="text"
                      icon={<BellOutlined />}
                      className="header-action-btn"
                    />
                  </Badge>
                </Popover>
              )}
              <Button
                type="text"
                icon={<StarFilled style={{ color: '#ffc107' }} />}
                className="header-action-btn"
              />
              {isAuthenticated ? (
                <Dropdown menu={{ items: userMenuItems, onClick: handleUserMenuClick }} placement="bottomRight">
                  <Space style={{ marginLeft: '8px', padding: '4px 12px', background: 'rgba(91, 124, 255, 0.1)', borderRadius: '12px', cursor: 'pointer' }}>
                    <Avatar
                      style={{ backgroundColor: '#5b7cff' }}
                      icon={<UserOutlined />}
                    />
                    <Text strong style={{ color: '#111827' }}>{user?.full_name || user?.username || '用户'}</Text>
                  </Space>
                </Dropdown>
              ) : (
                <Button type="primary" onClick={() => setAuthModalVisible(true)}>
                  登录 / 注册
                </Button>
              )}
            </Space>
          </div>
        </Header>

        <Content className="app-content-wrapper">
          <div className="content-container">
            {renderContent()}
          </div>
        </Content>
      </Layout>

      {/* 移动端浮动按钮 */}
      {isMobile && isAuthenticated && (
        <FloatButton
          icon={<PlusOutlined />}
          type="primary"
          onClick={() => {
            setCurrent('create')
          }}
          style={{ right: 24, bottom: 24 }}
        />
      )}

      <AuthModal visible={authModalVisible} onClose={() => setAuthModalVisible(false)} />
    </Layout>
  )
}

export default App

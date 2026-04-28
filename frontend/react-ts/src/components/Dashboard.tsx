import React, { useEffect, useState } from 'react'
import { Card, Row, Col, List, Tag, Progress, Skeleton, Typography, Alert, Space } from 'antd'
import {
  CheckCircleOutlined,
  ClockCircleOutlined,
  WarningOutlined,
  CalendarOutlined,
  RiseOutlined,
  BulbOutlined,
  CheckOutlined,
  ArrowRightOutlined
} from '@ant-design/icons'
import { useTaskStore } from '../store/taskStore'
import { taskApi } from '../api/taskApi'
import { DashboardData } from '../types/task'

const { Title, Text } = Typography

const metricConfig = [
  {
    key: 'total',
    label: '总任务数',
    footnote: '全部已创建事项',
    icon: <CalendarOutlined />,
    iconClass: 'is-blue'
  },
  {
    key: 'completed',
    label: '已完成',
    footnote: '保持执行节奏',
    icon: <CheckCircleOutlined />,
    iconClass: 'is-green'
  },
  {
    key: 'today_deadline',
    label: '今日到期',
    footnote: '建议优先处理',
    icon: <ClockCircleOutlined />,
    iconClass: 'is-gold'
  },
  {
    key: 'overdue',
    label: '已逾期',
    footnote: '需要尽快补救',
    icon: <WarningOutlined />,
    iconClass: 'is-red'
  }
] as const

const Dashboard: React.FC = () => {
  const { todayTasks, fetchTodayTasks, loading } = useTaskStore()
  const [dashboardData, setDashboardData] = useState<DashboardData | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const loadData = async () => {
      try {
        console.log('开始加载数据...')
        // 先测试直接调用API
        console.log('直接调用taskApi.getDashboard...')
        const res = await taskApi.getDashboard()
        console.log('taskApi.getDashboard调用完成，数据:', res)
        setDashboardData(res.data)
        console.log('数据加载成功')
        
        // 然后调用fetchTodayTasks
        console.log('调用fetchTodayTasks...')
        await fetchTodayTasks()
        console.log('fetchTodayTasks调用完成')
      } catch (err) {
        console.error('加载仪表盘数据失败:', err)
        setError('加载数据失败')
      }
    }
    loadData()
  }, [fetchTodayTasks])

  if (loading && !dashboardData) {
    return (
      <div className="page-section">
        <Skeleton active paragraph={{ rows: 2 }} />
        <Row gutter={[18, 18]} style={{ marginTop: 24 }}>
          {[1, 2, 3, 4].map(i => (
            <Col xs={24} sm={12} xl={6} key={i}>
              <Card className="surface-card">
                <Skeleton active avatar paragraph={{ rows: 1 }} />
              </Card>
            </Col>
          ))}
        </Row>
        <Row gutter={[18, 18]} style={{ marginTop: 24 }}>
          <Col span={10}><Card className="glass-card"><Skeleton active /></Card></Col>
          <Col span={14}><Card className="surface-card"><Skeleton active /></Card></Col>
        </Row>
      </div>
    )
  }

  if (error) {
    return <Alert message="错误" description={error} type="error" showIcon />
  }

  return (
    <div className="page-section">
      <div className="page-hero">
        <Text className="page-hero-kicker">Dashboard Overview</Text>
        <Title level={3} className="page-hero-title">
          今天的待办状态一目了然
        </Title>
        <Text className="page-hero-description">
          聚合总任务、完成率、今日到期和逾期事项，让你先抓住最重要的任务，再安排后续节奏。
        </Text>
      </div>

      <Row gutter={[18, 18]} className="stats-grid">
        {metricConfig.map((metric) => (
          <Col xs={24} sm={12} xl={6} key={metric.key}>
            <Card className="surface-card metric-card">
              <div className={`metric-icon ${metric.iconClass}`}>{metric.icon}</div>
              <Text className="metric-label">{metric.label}</Text>
              <div className="metric-value">
                {dashboardData?.stats[metric.key] || 0}
              </div>
              <Text className="metric-footnote">{metric.footnote}</Text>
            </Card>
          </Col>
        ))}
      </Row>

      <Row gutter={[18, 18]}>
        <Col xs={24} xl={10}>
          <Card className="glass-card">
            <Space direction="vertical" size={16} style={{ width: '100%' }}>
              <div>
                <Text className="page-kicker">效率趋势</Text>
                <Title level={4} className="section-title">
                  最近 7 天完成率
                </Title>
                <Text className="section-subtitle">
                  完成得越稳定，后续任务安排就越轻松。
                </Text>
              </div>
              <Progress
                percent={dashboardData?.stats.completion_rate || 0}
                strokeColor={{ '0%': '#5b7cff', '100%': '#39bdf8' }}
                trailColor="rgba(91, 124, 255, 0.12)"
                size={['100%', 14]}
              />
              <Space size={12}>
                <Tag color="blue" icon={<RiseOutlined />}>
                  进行中 {dashboardData?.stats.in_progress || 0}
                </Tag>
                <Tag color="gold">
                  待执行 {dashboardData?.stats.pending || 0}
                </Tag>
                <Tag color="red">
                  紧急 {dashboardData?.stats.urgent || 0}
                </Tag>
              </Space>
            </Space>
          </Card>
        </Col>
        <Col xs={24} xl={14}>
          <Card className="surface-card" style={{ height: '100%' }}>
            <Space direction="vertical" size={16} style={{ width: '100%' }}>
              <div>
                <Text className="page-kicker"><BulbOutlined /> AI 助手建议</Text>
                <Title level={4} className="section-title">
                  今日专注建议
                </Title>
                <Text className="section-subtitle">
                  基于当前任务进度，为您量身定制的执行策略。
                </Text>
              </div>
              
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                {[
                  { 
                    text: `今日到期 ${dashboardData?.stats.today_deadline || 0} 项，建议安排在优先时段处理`,
                    type: dashboardData?.stats.today_deadline ? 'warning' : 'success',
                    icon: <ClockCircleOutlined />
                  },
                  { 
                    text: `已有 ${dashboardData?.stats.completed || 0} 项完成，继续保持当前节奏`,
                    type: 'success',
                    icon: <CheckOutlined />
                  },
                  { 
                    text: `逾期 ${dashboardData?.stats.overdue || 0} 项，适合优先补齐关键任务`,
                    type: dashboardData?.stats.overdue ? 'danger' : 'success',
                    icon: <WarningOutlined />
                  }
                ].map((item, idx) => (
                  <div key={idx} style={{ 
                    padding: '12px 16px', 
                    borderRadius: 12, 
                    background: item.type === 'danger' ? '#fff1f0' : item.type === 'warning' ? '#fffbe6' : '#f6ffed',
                    border: `1px solid ${item.type === 'danger' ? '#ffa39e' : item.type === 'warning' ? '#ffe58f' : '#b7eb8f'}`,
                    display: 'flex',
                    alignItems: 'center',
                    gap: 12
                  }}>
                    <span style={{ color: item.type === 'danger' ? '#f5222d' : item.type === 'warning' ? '#faad14' : '#52c41a' }}>
                      {item.icon}
                    </span>
                    <Text style={{ flex: 1 }}>{item.text}</Text>
                    <ArrowRightOutlined style={{ color: 'rgba(0,0,0,0.25)' }} />
                  </div>
                ))}
              </div>
            </Space>
          </Card>
        </Col>
      </Row>

      <Row gutter={[18, 18]}>
        <Col xs={24} xl={12}>
          <Card
            title="今日到期任务"
            className="surface-card"
          >
            {todayTasks.length > 0 ? (
              <List
                dataSource={todayTasks}
                renderItem={(item) => (
                  <List.Item>
                    <List.Item.Meta
                      title={
                        <Space wrap>
                          <Text strong>{item.task}</Text>
                          <Tag color={item.priority === '高' ? 'red' : item.priority === '中' ? 'gold' : 'green'}>
                            {item.priority}
                          </Tag>
                        </Space>
                      }
                      description={`截止时间: ${item.deadline} | 分类: ${item.category}`}
                    />
                  </List.Item>
                )}
              />
            ) : (
              <div className="empty-state">今日无到期任务，安排得很从容。</div>
            )}
          </Card>
        </Col>
        <Col xs={24} xl={12}>
          <Card
            title="逾期任务"
            className="surface-card"
          >
            {dashboardData?.overdue_tasks && dashboardData.overdue_tasks.length > 0 ? (
              <List
                dataSource={dashboardData.overdue_tasks}
                renderItem={(item) => (
                  <List.Item>
                    <List.Item.Meta
                      title={
                        <Space wrap>
                          <Text type="danger" strong>{item.task}</Text>
                          <Tag color="red">{item.priority}</Tag>
                        </Space>
                      }
                      description={`截止时间: ${item.deadline} | 分类: ${item.category}`}
                    />
                  </List.Item>
                )}
              />
            ) : (
              <div className="empty-state">没有逾期任务，当前进度控制得不错。</div>
            )}
          </Card>
        </Col>
      </Row>
    </div>
  )
}

export default Dashboard

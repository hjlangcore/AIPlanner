import React, { useState, useEffect, useRef } from 'react'
import { Input, Button, Avatar, Card, Space, Typography, Spin, Empty, Tooltip, Drawer, List, Progress, Switch, Badge, Tag } from 'antd'
import { SendOutlined, UserOutlined, RobotOutlined, DownloadOutlined, PlusOutlined, CalendarOutlined, ClockCircleOutlined, AimOutlined, BarChartOutlined, HistoryOutlined, DeleteOutlined, ToolOutlined } from '@ant-design/icons'
import { useChatStore } from '../store/chatStore'
import { taskApi } from '../api/taskApi'

const { Text } = Typography
const { TextArea } = Input

const ChatComponent: React.FC = () => {
  const {
    sessions,
    currentSessionId,
    messages,
    loading,
    sending,
    agentMode,
    agentState,
    agentPlan,
    agentToolCalls,
    agentProgress,
    agentStreaming,
    fetchSessions,
    setCurrentSession,
    createSession,
    deleteSession,
    sendMessage,
    setAgentMode,
    sendAgentMessageStream
  } = useChatStore()
  
  const [inputValue, setInputValue] = useState('')
  const [historyVisible, setHistoryVisible] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    fetchSessions()
  }, [fetchSessions])

  useEffect(() => {
    if (sessions.length > 0 && !currentSessionId) {
      setCurrentSession(sessions[0].id)
    }
  }, [sessions, currentSessionId, setCurrentSession])

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  const handleSend = () => {
    if (!inputValue.trim() || sending) return
    if (agentMode) {
      sendAgentMessageStream(inputValue)
    } else {
      sendMessage(inputValue)
    }
    setInputValue('')
  }

  const handleNewChat = async () => {
    const sessionId = await createSession()
    setCurrentSession(sessionId)
  }

  const handleExport = () => {
    if (currentSessionId) {
      window.open(taskApi.exportChat(currentSessionId), '_blank')
    }
  }

  const handleDeleteSession = async (sessionId: string) => {
    await deleteSession(sessionId)
  }

  const quickReplies = [
    { text: "帮我创建一个明天下午 3 点的任务", icon: <CalendarOutlined /> },
    { text: "查看我今天到期的任务", icon: <ClockCircleOutlined /> },
    { text: "如何高效管理时间？", icon: <AimOutlined /> },
    { text: "总结一下本周的任务完成情况", icon: <BarChartOutlined /> }
  ]

  return (
    <div className="page-section" style={{ 
      height: 'calc(100vh - 180px)', 
      background: '#f8f9fa'
    }}>
      {/* 聊天主区域 */}
      <Card 
        className="surface-card" 
        style={{ 
          height: '100%',
          display: 'flex', 
          flexDirection: 'column',
          borderRadius: '0',
          boxShadow: 'none',
          border: '1px solid #e9ecef'
        }}
        styles={{ 
          body: { 
            padding: '0', 
            flex: 1, 
            display: 'flex', 
            flexDirection: 'column', 
            height: '100%',
            background: '#ffffff'
          },
          header: { 
            padding: '16px 20px',
            background: '#f8f9fa',
            borderBottom: '1px solid #e9ecef',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center'
          }
        }}
        title={
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <RobotOutlined style={{ color: '#16c784' }} />
            <Text style={{ fontSize: '16px', fontWeight: '600', color: '#343a40' }}>智能助手</Text>
            <span style={{ fontSize: '12px', color: '#16c784', marginLeft: '4px' }}>AI 驱动</span>
          </div>
        }
        extra={
          <Space size="small">
            <Space align="center">
              <RobotOutlined style={{ color: agentMode ? '#16c784' : '#6c757d' }} />
              <Switch 
                checked={agentMode} 
                onChange={setAgentMode} 
                checkedChildren="Agent模式" 
                unCheckedChildren="普通模式"
                size="small"
              />
            </Space>
            <Button 
              size="small"
              icon={<PlusOutlined />} 
              onClick={handleNewChat}
              style={{ 
                borderRadius: '4px',
                borderColor: '#ced4da',
                color: '#6c757d',
                height: '32px'
              }}
            >
              新对话
            </Button>
            <Button 
              size="small"
              icon={<HistoryOutlined />} 
              onClick={() => setHistoryVisible(true)}
              style={{ 
                borderRadius: '4px',
                borderColor: '#ced4da',
                color: '#6c757d',
                height: '32px'
              }}
            >
              历史记录
            </Button>
            <Tooltip title="导出对话记录">
              <Button 
                size="small"
                icon={<DownloadOutlined />} 
                onClick={handleExport}
                style={{ 
                  borderRadius: '4px',
                  borderColor: '#ced4da',
                  color: '#6c757d',
                  height: '32px'
                }}
              >
                导出
              </Button>
            </Tooltip>
          </Space>
        }
      >
        {currentSessionId ? (
          <>
            <div style={{ flex: 1, overflowY: 'auto', padding: '20px' }}>
              {loading ? (
                <div style={{ 
                  textAlign: 'center', 
                  marginTop: '60px'
                }}>
                  <Spin size="default" style={{ color: '#6c757d' }} />
                </div>
              ) : (
                <div>
                  {messages.length === 0 ? (
                    <div style={{ 
                      textAlign: 'center', 
                      marginTop: '80px',
                      padding: '40px 20px'
                    }}>
                      <Empty 
                        image={Empty.PRESENTED_IMAGE_SIMPLE} 
                        description="No data"
                      />
                    </div>
                  ) : (
                    messages.map((msg, index) => (
                      <div key={index} style={{ 
                        display: 'flex', 
                        justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start',
                        marginBottom: '16px'
                      }}>
                        <div style={{ 
                          display: 'flex', 
                          flexDirection: msg.role === 'user' ? 'row-reverse' : 'row',
                          maxWidth: '80%',
                          gap: '8px'
                        }}>
                          <Avatar 
                            icon={msg.role === 'user' ? <UserOutlined /> : <RobotOutlined />} 
                            style={{ 
                              backgroundColor: msg.role === 'user' ? '#007bff' : '#28a745',
                              flexShrink: 0,
                              width: '32px',
                              height: '32px',
                              fontSize: '14px'
                            }} 
                          />
                          <div style={{ 
                            padding: '10px 14px', 
                            borderRadius: msg.role === 'user' ? '16px 4px 16px 16px' : '4px 16px 16px 4px',
                            background: msg.role === 'user' ? '#007bff' : '#f1f3f5',
                            color: msg.role === 'user' ? '#fff' : '#343a40',
                            lineHeight: '1.4',
                            fontSize: '14px'
                          }}>
                            {msg.content}
                          </div>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              )}
              
              {/* Agent模式状态展示 */}
              {agentMode && (
                <div style={{ 
                  marginTop: '20px', 
                  padding: '16px', 
                  background: '#f8f9fa', 
                  borderRadius: '8px',
                  border: '1px solid #e9ecef'
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
                    <RobotOutlined style={{ color: '#16c784' }} />
                    <Text style={{ fontWeight: '600', fontSize: '14px' }}>AI Agent 状态</Text>
                    <Badge status={agentState === 'completed' ? 'success' : agentState === 'executing' ? 'processing' : 'default'} text={agentState} />
                  </div>
                  
                  {/* 执行进度 */}
                  {agentStreaming && (
                    <div style={{ marginBottom: '12px' }}>
                      <Text style={{ fontSize: '12px', color: '#6c757d', marginBottom: '4px', display: 'block' }}>执行进度</Text>
                      <Progress percent={agentProgress} size="small" status={agentProgress === 100 ? 'success' : 'active'} />
                    </div>
                  )}
                  
                  {/* 执行计划 */}
                  {agentPlan.length > 0 && (
                    <div style={{ marginBottom: '12px' }}>
                      <Text style={{ fontSize: '12px', color: '#6c757d', marginBottom: '8px', display: 'block' }}>执行计划</Text>
                      <div style={{ 
                        background: '#ffffff', 
                        padding: '12px', 
                        borderRadius: '4px',
                        border: '1px solid #e9ecef'
                      }}>
                        {agentPlan.map((step, index) => (
                          <div key={index} style={{ 
                            display: 'flex', 
                            alignItems: 'center', 
                            gap: '8px', 
                            marginBottom: '8px',
                            fontSize: '12px'
                          }}>
                            <div style={{ 
                              width: '20px', 
                              height: '20px', 
                              borderRadius: '50%', 
                              background: index < agentProgress/100*agentPlan.length ? '#16c784' : '#ced4da',
                              display: 'flex', 
                              alignItems: 'center', 
                              justifyContent: 'center',
                              color: '#ffffff',
                              fontSize: '10px'
                            }}>
                              {index + 1}
                            </div>
                            <div style={{ flex: 1 }}>
                              <Text style={{ fontSize: '12px' }}>{step.description}</Text>
                              {step.tool && (
                                <Tag style={{ marginTop: '4px', fontSize: '12px', padding: '2px 8px' }} color="blue">
                                  <ToolOutlined style={{ fontSize: '10px', marginRight: '4px' }} />
                                  {step.tool}
                                </Tag>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                  
                  {/* 工具调用记录 */}
                  {agentToolCalls.length > 0 && (
                    <div>
                      <Text style={{ fontSize: '12px', color: '#6c757d', marginBottom: '8px', display: 'block' }}>工具调用记录</Text>
                      <div style={{ 
                        background: '#ffffff', 
                        padding: '12px', 
                        borderRadius: '4px',
                        border: '1px solid #e9ecef',
                        maxHeight: '120px',
                        overflowY: 'auto'
                      }}>
                        {agentToolCalls.map((toolCall, index) => (
                          <div key={index} style={{ marginBottom: '8px', paddingBottom: '8px', borderBottom: '1px solid #f1f3f5' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '4px', marginBottom: '4px' }}>
                              <ToolOutlined style={{ fontSize: '12px', color: toolCall.success ? '#16c784' : '#dc3545' }} />
                              <Text style={{ fontSize: '12px', fontWeight: '500' }}>{toolCall.tool_name}</Text>
                              <Tag style={{ fontSize: '12px', padding: '2px 8px' }} color={toolCall.success ? 'green' : 'red'}>
                                {toolCall.success ? '成功' : '失败'}
                              </Tag>
                            </div>
                            <Text style={{ fontSize: '11px', color: '#6c757d', lineHeight: '1.3' }}>
                              参数: {JSON.stringify(toolCall.parameters)}
                            </Text>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
              
              {sending && (
                <div style={{ 
                  display: 'flex', 
                  gap: '8px', 
                  marginBottom: '16px'
                }}>
                  <Avatar 
                    icon={<RobotOutlined />} 
                    style={{ backgroundColor: '#28a745', width: '32px', height: '32px' }} 
                  />
                  <div style={{ 
                    padding: '10px 14px', 
                    borderRadius: '4px 16px 16px 4px', 
                    background: '#f1f3f5'
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <Spin size="small" style={{ color: '#6c757d' }} />
                      <Text style={{ color: '#6c757d', fontSize: '14px' }}>AI 正在思考...</Text>
                    </div>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>

            <div style={{ 
              padding: '16px', 
              borderTop: '1px solid #e9ecef', 
              background: '#f8f9fa'
            }}>
              <div style={{ marginBottom: '12px', display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                {quickReplies.map(reply => (
                  <Button 
                    key={reply.text} 
                    size="small" 
                    shape="round" 
                    onClick={() => setInputValue(reply.text)}
                    icon={reply.icon}
                    style={{
                      fontSize: '12px',
                      padding: '4px 12px',
                      borderRadius: '16px',
                      background: '#ffffff',
                      border: '1px solid #ced4da',
                      color: '#495057',
                      height: '28px'
                    }}
                  >
                    {reply.text}
                  </Button>
                ))}
              </div>
              <Space.Compact style={{ width: '100%' }}>
                <TextArea
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  placeholder={agentMode ? "输入复杂指令，AI Agent将自主完成多步骤任务..." : "输入消息，与智能助手对话..."}
                  autoSize={{ minRows: 1, maxRows: 3 }}
                  onPressEnter={(e) => {
                    if (!e.shiftKey) {
                      e.preventDefault()
                      handleSend()
                    }
                  }}
                  style={{
                    borderRadius: '4px 0 0 4px',
                    borderRight: 'none',
                    border: '1px solid #ced4da',
                    fontSize: '14px'
                  }}
                />
                <Button 
                  type="primary" 
                  icon={<SendOutlined />} 
                  onClick={handleSend}
                  loading={sending}
                  style={{
                    height: 'auto',
                    borderRadius: '0 4px 4px 0',
                    background: '#007bff',
                    border: 'none',
                    fontSize: '14px',
                    padding: '0 16px'
                  }}
                >
                  发送
                </Button>
              </Space.Compact>
            </div>
          </>
        ) : (
          <div style={{ 
            flex: 1, 
            display: 'flex', 
            alignItems: 'center', 
            justifyContent: 'center',
            background: '#f8f9fa'
          }}>
            <div style={{ 
              textAlign: 'center', 
              padding: '40px 20px'
            }}>
              <Empty 
                image={Empty.PRESENTED_IMAGE_SIMPLE} 
                description="No data"
              >
                <Button 
                  type="primary" 
                  icon={<PlusOutlined />}
                  onClick={handleNewChat}
                  style={{
                    marginTop: '16px',
                    background: '#007bff',
                    border: 'none'
                  }}
                >
                  开启新对话
                </Button>
              </Empty>
            </div>
          </div>
        )}

        {/* 历史记录抽屉 */}
        <Drawer
          title="聊天历史"
          placement="left"
          width={300}
          onClose={() => setHistoryVisible(false)}
          open={historyVisible}
        >
          <div style={{ padding: '16px 0' }}>
            <Button 
              type="primary" 
              icon={<PlusOutlined />} 
              block 
              onClick={handleNewChat}
              style={{ marginBottom: '16px' }}
            >
              开启新对话
            </Button>
            <List
              dataSource={sessions}
              renderItem={(item) => (
                <List.Item
                  onClick={() => {
                    setCurrentSession(item.id)
                    setHistoryVisible(false)
                  }}
                  style={{
                    cursor: 'pointer',
                    borderRadius: '8px',
                    padding: '12px 16px',
                    marginBottom: '8px',
                    background: currentSessionId === item.id ? '#e6f7ff' : '#ffffff',
                    border: '1px solid #e8e8e8'
                  }}
                  actions={[
                    <Button
                      key="delete"
                      size="small"
                      danger
                      icon={<DeleteOutlined />}
                      onClick={(e) => {
                        e.stopPropagation()
                        handleDeleteSession(item.id)
                      }}
                    />
                  ]}
                >
                  <div style={{ width: '100%' }}>
                    <Text ellipsis style={{ fontWeight: currentSessionId === item.id ? '600' : 'normal' }}>
                      {item.title}
                    </Text>
                    <div style={{ marginTop: '4px' }}>
                      <Text type="secondary" style={{ fontSize: '12px' }}>
                        {new Date(item.created_at).toLocaleString('zh-CN', {
                          month: '2-digit',
                          day: '2-digit',
                          hour: '2-digit',
                          minute: '2-digit'
                        })}
                      </Text>
                    </div>
                  </div>
                </List.Item>
              )}
            />
          </div>
        </Drawer>
      </Card>
    </div>
  )
}

export default ChatComponent

import React, { useEffect, useState } from 'react'
import { Card, Typography, Modal, Form, Input, Select, Button, Tag, Space } from 'antd'
import FullCalendar from '@fullcalendar/react'
import dayGridPlugin from '@fullcalendar/daygrid'
import interactionPlugin from '@fullcalendar/interaction'
import { useTaskStore } from '../store/taskStore'
import { TaskStatus } from '../types/task'
import { taskApi } from '../api/taskApi'
import { toast } from 'react-toastify'

const { Title, Text } = Typography
const { Option } = Select

type CalendarTaskFormValues = {
  task: string
  priority?: string
}

const CalendarView: React.FC = () => {
  const { tasks, fetchTasks, loading } = useTaskStore()
  const [events, setEvents] = useState<any[]>([])
  const [isModalVisible, setIsModalVisible] = useState(false)
  const [selectedDate, setSelectedDate] = useState<string>('')
  const [form] = Form.useForm()
  const [selectedEvent, setSelectedEvent] = useState<any>(null)
  const [isDetailModalVisible, setIsDetailModalVisible] = useState(false)

  useEffect(() => {
    fetchTasks()
  }, [fetchTasks])

  useEffect(() => {
    // 转换任务为日历事件
    const calendarEvents = tasks.map(task => ({
      id: task.id.toString(),
      title: task.raw_task.length > 20 ? task.raw_task.substring(0, 20) + '...' : task.raw_task,
      start: task.deadline,
      end: task.deadline,
      color: getEventColor(task.priority, task.status),
      allDay: true,
      description: `优先级: ${task.priority}\n状态: ${task.status}\n分类: ${task.category}`,
      task: task
    }))
    setEvents(calendarEvents)
  }, [tasks])

  const getEventColor = (priority: string, status: string) => {
    // 根据状态和优先级设置颜色
    if (status === '已完成') {
      return '#52c41a' // 绿色
    } else if (status === '已过期') {
      return '#f5222d' // 红色
    } else {
      switch (priority) {
        case '高': return '#f5222d' // 红色
        case '中': return '#faad14' // 橙色
        case '低': return '#1890ff' // 蓝色
        default: return '#1890ff' // 蓝色
      }
    }
  }

  const handleDateClick = (info: any) => {
    setSelectedDate(info.dateStr)
    form.resetFields()
    setIsModalVisible(true)
  }

  const handleEventClick = (info: any) => {
    setSelectedEvent(info.event)
    setIsDetailModalVisible(true)
  }

  const handleCreateTask = async (values: CalendarTaskFormValues) => {
    try {
      const rawInput = `${values.task} ${selectedDate}`
      const res = await taskApi.createTask({ raw_input: rawInput })
      if (res.data.success) {
        toast.success('任务创建成功！')
        await fetchTasks()
        setIsModalVisible(false)
      } else {
        toast.error('任务创建失败，请重试')
      }
    } catch (error) {
      toast.error('任务创建失败，请重试')
      console.error('创建任务失败:', error)
    }
  }

  const handleUpdateStatus = async (taskId: number, status: TaskStatus) => {
    try {
      await taskApi.updateTaskStatus(taskId, status)
      toast.success('任务状态更新成功！')
      await fetchTasks()
      setIsDetailModalVisible(false)
    } catch (error) {
      toast.error('任务状态更新失败，请重试')
      console.error('更新任务状态失败:', error)
    }
  }

  return (
    <div className="page-section">
      <div className="page-hero">
        <Text className="page-hero-kicker">Calendar Planner</Text>
        <Title level={3} className="page-hero-title">
          用时间视角查看任务分布
        </Title>
        <Text className="page-hero-description">
          点击日期可快速创建任务，点击日程可查看详情并直接更新状态，适合安排每日节奏和检查冲突。
        </Text>
      </div>

      <Card className="surface-card calendar-shell calendar-container">
        <FullCalendar
          plugins={[dayGridPlugin, interactionPlugin]}
          initialView="dayGridMonth"
          events={events}
          dateClick={handleDateClick}
          eventClick={handleEventClick}
          locale="zh-cn"
          headerToolbar={{
            left: 'prev,next today',
            center: 'title',
            right: 'dayGridMonth,dayGridWeek,dayGridDay'
          }}
          height="620px"
          eventContent={(eventInfo) => (
            <div style={{ padding: '4px', fontSize: '12px' }}>
              <b style={{ display: 'block', marginBottom: '4px' }}>{eventInfo.event.title}</b>
              <Space size={4} wrap>
                <Tag color={eventInfo.event.backgroundColor}>
                  {eventInfo.event.extendedProps.task.priority}
                </Tag>
                <Tag
                  color={
                    eventInfo.event.extendedProps.task.status === '已完成'
                      ? 'green'
                      : eventInfo.event.extendedProps.task.status === '已过期'
                        ? 'red'
                        : 'blue'
                  }
                >
                  {eventInfo.event.extendedProps.task.status}
                </Tag>
              </Space>
            </div>
          )}
          eventDidMount={(info) => {
            info.el.title = info.event.extendedProps.description
          }}
        />
      </Card>

      <Modal
        title="创建任务"
        open={isModalVisible}
        onCancel={() => setIsModalVisible(false)}
        footer={null}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleCreateTask}
        >
          <Form.Item
            name="task"
            label="任务描述"
            rules={[{ required: true, message: '请输入任务描述' }]}
          >
            <Input placeholder="请输入任务描述，例如：准备周会材料" />
          </Form.Item>
          <Form.Item
            name="priority"
            label="优先级"
            initialValue="中"
          >
            <Select>
              <Option value="高">高</Option>
              <Option value="中">中</Option>
              <Option value="低">低</Option>
            </Select>
          </Form.Item>
          <Form.Item
            label="日期"
          >
            <Text>{selectedDate}</Text>
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" loading={loading} size="large">
              创建任务
            </Button>
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title="任务详情"
        open={isDetailModalVisible}
        onCancel={() => setIsDetailModalVisible(false)}
        footer={null}
      >
        {selectedEvent && (
          <div>
            <div className="modal-info-row">
              <Text className="modal-info-label">任务</Text>
              <Text strong>{selectedEvent.extendedProps.task.raw_task}</Text>
            </div>
            <div className="modal-info-row">
              <Text className="modal-info-label">优先级</Text>
              <Tag color={getEventColor(selectedEvent.extendedProps.task.priority, selectedEvent.extendedProps.task.status)}>
                {selectedEvent.extendedProps.task.priority}
              </Tag>
            </div>
            <div className="modal-info-row">
              <Text className="modal-info-label">状态</Text>
              <Tag color={selectedEvent.extendedProps.task.status === '已完成' ? 'green' : selectedEvent.extendedProps.task.status === '已过期' ? 'red' : 'blue'}>
                {selectedEvent.extendedProps.task.status}
              </Tag>
            </div>
            <div className="modal-info-row">
              <Text className="modal-info-label">截止日期</Text>
              <Text>{selectedEvent.extendedProps.task.deadline}</Text>
            </div>
            <div className="modal-info-row">
              <Text className="modal-info-label">分类</Text>
              <Text>{selectedEvent.extendedProps.task.category}</Text>
            </div>
            <div className="modal-info-row">
              <Text className="modal-info-label">进度</Text>
              <Text>{selectedEvent.extendedProps.task.progress}%</Text>
            </div>
            <div className="modal-info-row">
              <Text className="modal-info-label">创建时间</Text>
              <Text>{selectedEvent.extendedProps.task.create_time}</Text>
            </div>
            <div className="modal-info-row">
              <Text className="modal-info-label">更新时间</Text>
              <Text>{selectedEvent.extendedProps.task.update_time}</Text>
            </div>
            <div style={{ marginTop: '20px' }}>
              <Button
                type="primary"
                onClick={() => handleUpdateStatus(selectedEvent.extendedProps.task.id, '已完成')}
                style={{ marginRight: '8px' }}
              >
                标记为已完成
              </Button>
              <Button
                onClick={() => handleUpdateStatus(selectedEvent.extendedProps.task.id, '进行中')}
                style={{ marginRight: '8px' }}
              >
                标记为进行中
              </Button>
              <Button
                danger
                onClick={() => handleUpdateStatus(selectedEvent.extendedProps.task.id, '已过期')}
              >
                标记为已过期
              </Button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  )
}

export default CalendarView

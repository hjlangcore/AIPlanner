import React, { useState } from 'react'
import { Modal, Form, Input, Button, Tabs, message, Typography } from 'antd'
import { UserOutlined, LockOutlined, MailOutlined, IdcardOutlined } from '@ant-design/icons'
import { useAuthStore } from '../store/authStore'

const { Text } = Typography

interface AuthModalProps {
  visible: boolean
  onClose: () => void
}

const AuthModal: React.FC<AuthModalProps> = ({ visible, onClose }) => {
  const [activeTab, setActiveTab] = useState('login')
  const [loading, setLoading] = useState(false)
  const { login, register } = useAuthStore()

  const onFinish = async (values: any) => {
    setLoading(true)
    try {
      if (activeTab === 'login') {
        await login({ username: values.username, password: values.password })
        message.success('登录成功')
        onClose()
      } else {
        await register({
          username: values.username,
          password: values.password,
          full_name: values.full_name,
          email: values.email
        })
        message.success('注册成功，请登录')
        setActiveTab('login')
      }
    } catch (error: any) {
      message.error(error.response?.data?.detail || '操作失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Modal
      title={null}
      open={visible}
      onCancel={onClose}
      footer={null}
      width={400}
      centered
      styles={{ body: { padding: '24px 32px' } }}
    >
      <div style={{ textAlign: 'center', marginBottom: '24px' }}>
        <div style={{ 
          width: '64px', 
          height: '64px', 
          background: 'linear-gradient(135deg, #5b7cff, #39bdf8)', 
          borderRadius: '20px',
          display: 'inline-flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: '#fff',
          fontSize: '32px',
          marginBottom: '12px',
          boxShadow: '0 8px 16px rgba(91, 124, 255, 0.25)'
        }}>
          ✨
        </div>
        <div style={{ fontSize: '20px', fontWeight: 700, color: '#111827' }}>欢迎来到智能记录中心</div>
        <Text type="secondary">开启你的智能高效生活</Text>
      </div>

      <Tabs 
        activeKey={activeTab} 
        onChange={setActiveTab} 
        centered
        items={[
          {
            key: 'login',
            label: '用户登录',
            children: (
              <Form onFinish={onFinish} layout="vertical">
                <Form.Item
                  name="username"
                  rules={[
                    { required: true, message: '请输入用户名' },
                    { pattern: /^[a-zA-Z0-9]+$/, message: '用户名只能包含字母或数字' }
                  ]}
                >
                  <Input prefix={<UserOutlined />} placeholder="用户名 (字母或数字)" size="large" />
                </Form.Item>
                <Form.Item
                  name="password"
                  rules={[
                    { required: true, message: '请输入密码' },
                    { pattern: /^[a-zA-Z0-9]+$/, message: '密码只能包含字母或数字' }
                  ]}
                >
                  <Input.Password prefix={<LockOutlined />} placeholder="密码" size="large" />
                </Form.Item>
                <Form.Item>
                  <Button type="primary" htmlType="submit" block size="large" loading={loading}>
                    立即登录
                  </Button>
                </Form.Item>
              </Form>
            )
          },
          {
            key: 'register',
            label: '新用户注册',
            children: (
              <Form onFinish={onFinish} layout="vertical">
                <Form.Item
                  name="username"
                  rules={[
                    { required: true, message: '请输入用户名' },
                    { pattern: /^[a-zA-Z0-9]+$/, message: '用户名只能包含字母或数字' }
                  ]}
                >
                  <Input prefix={<UserOutlined />} placeholder="用户名 (字母或数字)" size="large" />
                </Form.Item>
                <Form.Item
                  name="full_name"
                >
                  <Input prefix={<IdcardOutlined />} placeholder="真实姓名 (可选)" size="large" />
                </Form.Item>
                <Form.Item
                  name="email"
                  rules={[{ type: 'email', message: '请输入有效的邮箱' }]}
                >
                  <Input prefix={<MailOutlined />} placeholder="电子邮箱 (可选)" size="large" />
                </Form.Item>
                <Form.Item
                  name="password"
                  rules={[
                    { required: true, message: '请输入密码' },
                    { pattern: /^[a-zA-Z0-9]+$/, message: '密码只能包含字母或数字' },
                    { min: 3, message: '密码至少3位' }
                  ]}
                >
                  <Input.Password prefix={<LockOutlined />} placeholder="设置密码 (字母或数字)" size="large" />
                </Form.Item>
                <Form.Item>
                  <Button type="primary" htmlType="submit" block size="large" loading={loading}>
                    注册账号
                  </Button>
                </Form.Item>
              </Form>
            )
          }
        ]}
      />
    </Modal>
  )
}

export default AuthModal

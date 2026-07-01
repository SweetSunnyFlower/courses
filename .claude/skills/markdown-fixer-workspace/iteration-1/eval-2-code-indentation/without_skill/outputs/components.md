# TypeScript 组件文档

## Button 组件

一个可复用的按钮组件：

```tsx
import React from 'react';

interface ButtonProps {
  label: string;
  onClick: () => void;
  variant?: 'primary' | 'secondary';
  disabled?: boolean;
}

export const Button: React.FC<ButtonProps> = ({ label, onClick, variant = 'primary', disabled = false }) => {
  const className = `btn btn-${variant} ${disabled ? 'btn-disabled' : ''}`;
  return (
    <button
      className={className}
      onClick={onClick}
      disabled={disabled}
    >
      {label}
    </button>
  );
};
```

## 配置文件

```json
{
  "name": "my-app",
  "version": "1.0.0",
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "typescript": "^5.0.0"
  },
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "test": "vitest"
  }
}
```

## Hook 示例

```tsx
import { useState, useEffect } from 'react';

export function useLocalStorage<T>(key: string, initialValue: T) {
  const [storedValue, setStoredValue] = useState<T>(() => {
    try {
      const item = window.localStorage.getItem(key);
      return item ? JSON.parse(item) : initialValue;
    } catch (error) {
      return initialValue;
    }
  });

  useEffect(() => {
    window.localStorage.setItem(key, JSON.stringify(storedValue));
  }, [key, storedValue]);

  return [storedValue, setStoredValue] as const;
}
```

## 简单 JSON 配置

```json
{
  "theme": "dark",
  "language": "zh-CN",
  "features": {
    "darkMode": true,
    "notifications": false
  }
}
```

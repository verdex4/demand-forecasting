import { JSX, memo, useEffect, useMemo, useState } from 'react';
import { Table } from 'antd';
import type { TableProps } from 'antd';
import { usePlanVsFact } from '@/Hooks/usePlanVsFact';
import styles from './Styles.module.scss';

interface MetricRow {
  key: string;
  method: string;
  methodRowSpan: number;
  metricName: string;
  errors: Record<number, number | null>;
  isFirstInGroup: boolean;
  groupIndex: number;
}

function PlanVsFactComponent(): JSX.Element {
  const { data, loading, error, fetchErrors } = usePlanVsFact();
  const [hoveredGroupIndex, setHoveredGroupIndex] = useState<number | null>(null);
  const [isMethodHovered, setIsMethodHovered] = useState(false);
  const [hoveredRowKey, setHoveredRowKey] = useState<string | null>(null);

  useEffect(() => {
    fetchErrors();
  }, [fetchErrors]);

  const years = useMemo(() => {
    if (!data.length) return [];
    const allYears = new Set<number>();
    data.forEach((methodData) => {
      methodData.metrics.forEach((metric) => {
        Object.keys(metric.errors).forEach((year) => allYears.add(Number(year)));
      });
    });
    return Array.from(allYears).sort((a, b) => a - b);
  }, [data]);

  const dataSource = useMemo(() => {
    const rows: MetricRow[] = [];
    data.forEach((group, groupIdx) => {
      const count = group.metrics.length;
      group.metrics.forEach((metric, idx) => {
        rows.push({
          key: `${group.method}-${metric.name}`,
          method: group.method,
          methodRowSpan: idx === 0 ? count : 0,
          metricName: metric.name,
          errors: metric.errors,
          isFirstInGroup: idx === 0,
          groupIndex: groupIdx,
        });
      });
    });
    return rows;
  }, [data]);

const columns: TableProps<MetricRow>['columns'] = [
  {
    title: 'Метод прогнозирования',
    dataIndex: 'method',
    width: 220,
    onCell: (record) => ({
      rowSpan: record.methodRowSpan,
      onMouseEnter: () => {
        if (record.methodRowSpan > 0) {
          setIsMethodHovered(true);
          setHoveredGroupIndex(record.groupIndex);
          setHoveredRowKey(null);
        }
      },
      onMouseLeave: () => {
        setIsMethodHovered(false);
        setHoveredGroupIndex(null);
      },
      style: {
        verticalAlign: 'middle',
        fontWeight: 600,
        color: 'var(--blue-primary, #3b82f6)',
        borderRight: '2px solid var(--border-primary, rgba(255,255,255,0.15))',
      } as React.CSSProperties,
    }),
  },
  {
    title: 'Показатель',
    dataIndex: 'metricName',
    className: styles.metricNameColumn,
    onHeaderCell: () => ({
      style: {
        paddingLeft: '18px',
      } as React.CSSProperties,
    }),
    onCell: () => ({
      style: {
        paddingLeft: '18px',
        color: 'var(--text-secondary)',
      } as React.CSSProperties,
    }),
  },
  // ✅ Обёртка "Год" с children
  {
    title: 'Год',
    align: 'center' as const,
    children: years.map((year) => ({
      title: String(year),
      dataIndex: 'errors',
      key: String(year),
      width: 120,
      align: 'center' as const,
      render: (errors: Record<number, number | null>) => {
        const err = errors[year];
        if (err !== null && err !== undefined) {
          let color = '';
          if (err >= 20) { color = 'var(--red-primary, #ef4444)'; }
          else if (err >= 10) { color = 'var(--yellow-primary, #fbbf24)'; }
          else { color = 'var(--green-primary, #22c55e)'; }
          return (
            <span
              style={{
                color: color,
                fontWeight: 600,
              } as React.CSSProperties}
            >
              {err}%
            </span>
          );
        }
        return (
          <span style={{ color: 'var(--text-muted)', fontStyle: 'italic', fontSize: '13px' } as React.CSSProperties}>
            Н/Д
          </span>
        );
      },
      onCell: () => ({
        style: {
          textAlign: 'center' as const,
        } as React.CSSProperties,
      }),
    })),
  },
];

  if (loading) {
    return (
      <div className={styles.page}>
        <div className={styles.container}>
          <div className={styles.empty}>Загрузка данных...</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={styles.page}>
        <div className={styles.container}>
          <div className={styles.empty} style={{ color: 'var(--red-primary, #ef4444)' }}>
            Ошибка: {error}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.page}>
      <style>{`
        .${styles.antTable} .ant-table-tbody > tr:hover > td,
        .${styles.antTable} .ant-table-tbody > tr.ant-table-row-hover > td {
          background: transparent !important;
        }
        .${styles.antTable} .ant-table-tbody > tr.${styles.groupHoverRow} > td,
        .${styles.antTable} .ant-table-tbody > tr.${styles.singleRowHover} > td {
          background: var(--hover-bg, rgba(255,255,255,0.05)) !important;
        }
      `}</style>
      <div className={styles.header}>
        <h1 className={styles.title}>Точность модели</h1>
        <p className={styles.subtitle}>
          Оценка ошибки прогнозирования на исторических данных
        </p>
      </div>
      <div className={styles.container}>
        {data.length === 0 ? (
          <div className={styles.empty}>Нет данных для отображения</div>
        ) : (
          <div className={styles.tableWrapper}>
            <Table<MetricRow>
              columns={columns}
              dataSource={dataSource}
              pagination={false}
              showHeader={true}
              rowClassName={(record) => {
                const classes: string[] = [];
                if (record.isFirstInGroup) classes.push(styles.groupHeaderRow);
                if (isMethodHovered && record.groupIndex === hoveredGroupIndex) {
                  classes.push(styles.groupHoverRow);
                } else if (hoveredRowKey === record.key) {
                  classes.push(styles.singleRowHover);
                }
                return classes.join(' ');
              }}
              onRow={(record) => ({
                onMouseEnter: () => {
                  if (!isMethodHovered) {
                    setHoveredRowKey(record.key);
                  }
                },
                onMouseLeave: () => {
                  setHoveredRowKey(null);
                },
              })}
              className={styles.antTable}
              size="middle"
            />
          </div>
        )}
      </div>
      
      <div className={styles.container}>
        <p>Пояснение:</p>
      <ul>
        <li>Исторические данные берутся с 2019 по тестируемый год минус 1, прогноз делается на тестируемый год и сравнивается с фактом</li>
        <li>Для расчёта ошибки используется взвешенная процентная ошибка wMAPE = sum(|Факт - Прогноз|) / sum(|Факт|)</li>
        <li>Цветовая разметка ошибок: 🔴 &gt; 20% | 🟡 10%–20% | 🟢 &lt; 10%</li>
      </ul>
      </div>
    
    </div>
  );
}

export const PlanVsFact = memo(PlanVsFactComponent);
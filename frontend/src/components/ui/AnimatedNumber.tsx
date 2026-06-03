import { useSpring, animated } from '@react-spring/web'

interface AnimatedNumberProps {
  value: number
  duration?: number
  className?: string
}

export function AnimatedNumber({ value, duration = 1100, className }: AnimatedNumberProps) {
  const { n } = useSpring({
    from: { n: 0 },
    to: { n: value },
    config: { duration },
    reset: true,
  })

  return (
    <animated.span className={className}>
      {n.to(x => Math.floor(x).toString())}
    </animated.span>
  )
}

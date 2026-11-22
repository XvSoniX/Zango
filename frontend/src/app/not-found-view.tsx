import { Link } from 'react-router'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'

export function NotFoundView() {
  return (
    <main
      role="region"
      aria-label="Not Found"
      data-slot="not-found-view"
      className="flex min-h-screen flex-col items-center justify-center p-4"
    >
      <Card className="w-full max-w-sm text-center">
        <CardHeader>
          <CardTitle className="text-2xl font-bold">404</CardTitle>
          <CardDescription>The requested page could not be found.</CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            Please check the URL or navigate back to the home view.
          </p>
        </CardContent>
        <CardFooter className="justify-center">
          <Button asChild variant="default">
            <Link to="/">Back to Home</Link>
          </Button>
        </CardFooter>
      </Card>
    </main>
  )
}
